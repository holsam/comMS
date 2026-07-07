'''
comMS lfq functions
'''

# -- Import external dependencies
import pandas as pd
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.context import ExperimentContext, resolve_mzml_files, resolve_results_input, resolve_sample_sheet
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil
from comms.utils import samples as samputil

# -- run_lfq: runs lfq (FlashLFQ) on all PSM/mzML files and writes results to output
def run_lfq(
        rescore_dir,
        data_files,
        sample_sheet,
        ctx: ExperimentContext,
        in_pipeline: bool = False
    ):
    if not in_pipeline:
        logMsg('lfq')
    logMsg.debug('Started command: lfq')
    crux_bin, _ = validate(check_crux=True, allow_lfq=True, bin_dir=ctx.bin_dir)
    rescore_dir = resolve_results_input(ctx, 'rescore', rescore_dir)
    mzml_files = resolve_mzml_files(ctx, data_files)
    sample_sheet = resolve_sample_sheet(ctx, sample_sheet)
    psm_files = sorted(rescore_dir.glob('[!.]*.percolator.target.psms.txt'))
    if not psm_files:
        logMsg.warn(f'No rescored PSMs found in {rescore_dir}')
        raise SystemExit(1)
    logMsg.info(f'Running LFQ on {len(psm_files)} PSM file(s)')
    samples = samputil.loadSampleSheet(sample_sheet)
    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'lfq')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'lfq.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    fraction_groups = _groupPsmsByFraction(psm_files, samples)
    for fraction, fraction_psms in fraction_groups.items():
        logMsg.info(f'Running LFQ for fraction {fraction} ({len(fraction_psms)} file(s))')
        out_dir_fraction = out_dir / fraction
        out_dir_fraction.mkdir(parents=True, exist_ok=True)
        ok = cruxutil.lfq(
            crux_bin=crux_bin,
            psm_files=fraction_psms,
            mzml_files=mzml_files,
            out_dir=out_dir_fraction,
            fileroot=fraction,
            config=ctx.config,
        )
        if not ok:
            logMsg.warn(f'LFQ failed for fraction: {fraction}')
    logMsg.info(f'LFQ complete: {len(fraction_groups)} quantified')
    logMsg.debug('Finished command: lfq')

# -- _groupPsmsByFraction: return dictionary mapping fraction labels to PSM file paths
def _groupPsmsByFraction(psm_files: list[Path], samples: pd.DataFrame) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    if samples.empty:
        logMsg.warn(f'Sample sheet has no entries')
        return groups
    for psm_file in psm_files:
        stem = psm_file.name.removesuffix('.percolator.target.psms.txt')
        samples['file_stem'] = samples.apply(_get_stem, axis=1)
        match = samples[samples['file_stem'] == stem]
        if match.empty:
            logMsg.warn(f'No sample sheet entry for {psm_file.name}')
            continue
        fraction = match.iloc[0]['fraction']
        groups.setdefault(fraction, []).append(psm_file)
        logMsg.debug(f'{psm_file.name} assigned to fraction {fraction}')
    return groups

# -- _get_stem: return str corresponding to stem of file from raw_file in sample sheet
def _get_stem(row):
    return str(row['sample_id'])