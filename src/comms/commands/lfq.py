'''
comMS lfq functions
'''

# -- Import external dependencies
import pandas as pd
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil
from comms.utils import samples as samputil

# -- run_lfq: runs lfq (FlashLFQ) on all PSM/mzML files and writes results to output
def run_lfq(
    rescore_dir: Path,
    mzml_dir: Path,
    sample_sheet: Path,
    output: Path,
    mbr: bool | None,
    in_pipeline: bool = False
):
    '''
    Run crux lfq
    '''
    if not in_pipeline:
        log = logMsg('lfq')
        log.debug('Starting LFQ command')
    logMsg.debug('Locating Crux binary')
    bin_dir = pathutil.repoBinDir()
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        logMsg.error(f'Crux binary not found under: {bin_dir}')
        raise SystemExit(1)

    logMsg.debug(f'Scanning for rescored PSM files in: {rescore_dir}')
    psm_files = sorted(rescore_dir.glob('*.percolator.target.psms.txt'))
    if not psm_files:
        logMsg.warn(f'No rescored PSM files found in {rescore_dir}')
        raise SystemExit(1)
    logMsg.info(f'Found {len(psm_files)} rescored PSM file(s)')
    
    logMsg.debug(f'Scanning for mzML files in: {mzml_dir}')
    mzml_files = sorted(list(mzml_dir.glob('*.mzML')) + list(mzml_dir.glob('*.mzML.gz')))
    if not mzml_files:
        logMsg.warn(f'No mzML files found in: {mzml_dir}')
        raise SystemExit(1)
    logMsg.info(f'Found {len(mzml_files)} mzML file(s)')

    samples = samputil.loadSampleSheet(sample_sheet)
    psm_files = sorted(rescore_dir.glob('*.percolator.target.psms.txt'))
    out_dir = pathutil.generateOutputFileStructure(output, 'lfq')
    fraction_groups = _groupPsmsByFraction(psm_files, samples)
    for fraction, fraction_psms in fraction_groups.items():
        logMsg.info(f'Running LFQ for fraction: {fraction} ({len(fraction_psms)} files(s))')
        out_dir_fraction = out_dir / fraction
        out_dir_fraction.mkdir(parents=True, exist_ok=True)
        ok = cruxutil.lfq(
            crux_bin=crux_bin,
            psm_files=fraction_psms,
            mzml_dir=mzml_dir,
            out_dir=out_dir_fraction,
            fileroot=fraction,
            config=config,
            match_between_runs=mbr,
        )
        if not ok:
            logMsg.warn(f'LFQ failed for fraction: {fraction}')


# -- _groupPsmsByFraction: return dictionary mapping fraction labels to PSM file paths
def _groupPsmsByFraction(psm_files: list[Path], samples: pd.DataFrame) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    if samples.empty:
        logMsg.warn(f'Sample sheet does not contain any entries')
        return groups
    for psm_file in psm_files:
        stem = psm_file.name.removesuffix('.percolator.target.psms.txt')
        samples['file_stem'] = samples.apply(_get_stem, axis=1)
        match = samples[samples['file_stem'] == stem]
        if match.empty:
            logMsg.warn(f'No sample sheet entry found for PSM file: {psm_file.name}')
            continue
        fraction = match.iloc[0]['fraction']
        groups.setdefault(fraction, []).append(psm_file)
    return groups

# -- _get_stem: return str corresponding to stem of file from raw_file in sample sheet
def _get_stem(row):
    return Path(row['raw_file']).stem