'''
comMS search functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.context import ExperimentContext, resolve_results_input, resolve_mzml_files
from comms.utils.settings import resolve_config_value, _writeConfigTo
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_search: runs tide-search on all mzML files in input_dir and writes results to output
def run_search(
        data_files,
        index_dir,
        ctx: ExperimentContext,
        param_medic: bool,
        threads: int | None,
        score_function: str | None = None,
        min_peaks: int | None = None,
        precursor_tolerance_ppm: float | None = None,
        mz_bin_width: float | None = None,
        in_pipeline: bool = False,
):
    if not in_pipeline:
        logMsg('search')
    logMsg.debug('Started command: search')
    crux_bin, _ = validate(check_crux=True, bin_dir=ctx.bin_dir)
    index_dir = resolve_results_input(ctx, 'index', index_dir)
    mzml_files = resolve_mzml_files(ctx, data_files)
    logMsg.info(f'Searching {len(mzml_files)} mzML file(s)')
    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'search')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'search.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')

    # -- Optional: param-medic tolerance estimation
    pm_precursor, pm_bin_width = None, None
    if param_medic:
        logMsg.progress(f'Estimating tolerances with param-medic')
        pm_precursor, pm_bin_width = _runParamMedic(crux_bin=crux_bin, mzml_files=mzml_files, out_dir=out_dir)
    
    # Build config for this run only if any override was given
    overrides_given = any(v is not None for v in (threads, score_function, min_peaks, precursor_tolerance_ppm, mz_bin_width))
    if overrides_given:
        logMsg.debug('Using run-specific configuration parameters')
        run_config = {**ctx.config, 'search': dict(ctx.config.get('search', {}))}
        run_config['search']['threads'] = resolve_config_value(ctx.config, 'search', 'threads', threads)
        run_config['search']['score_function'] = resolve_config_value(ctx.config, 'search', 'score_function', score_function)
        run_config['search']['min_peaks'] = resolve_config_value(ctx.config, 'search', 'min_peaks', min_peaks)
        run_config['search']['precursor_tolerance_ppm'] = resolve_config_value(ctx.config, 'search', 'precursor_tolerance_ppm', precursor_tolerance_ppm if precursor_tolerance_ppm is not None else pm_precursor)
        run_config['search']['mz_bin_width'] = resolve_config_value(ctx.config, 'search', 'mz_bin_width', mz_bin_width if mz_bin_width is not None else pm_bin_width)
        logMsg.info('Command-line overrides detected - run configuration file will be saved to output folder as "search.config.toml"')
        _writeConfigTo(run_config, path=Path(out_dir, 'search.config.toml'))
    else:
        logMsg.debug('Using contextual configuration parameters')
        run_config = ctx.config

    logMsg.debug(f'Precursor tolerance {run_config["search"]["precursor_tolerance_ppm"]} ppm, m/z bin width {run_config["search"]["mz_bin_width"]} Da')

    # -- PSM search
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for mzml_file in tqdm(mzml_files, desc='Files searched'):
            logMsg.progress(f'Searching {mzml_file.name}')
            fileroot = mzml_file.name.removesuffix('.gz').removesuffix('.mzML')
            ok = cruxutil.tideSearch(
                crux_bin=crux_bin,
                mzml_file=mzml_file,
                index_dir=index_dir,
                out_dir=out_dir,
                fileroot=fileroot,
                config=run_config,
            )
            if ok:
                n_ok += 1
            else:
                logMsg.warn(f'Tide-search failed for {mzml_file.name}')
                n_fail += 1
    logMsg.info(f'Search complete: {n_ok} succeeded, {n_fail} failed')
    logMsg.debug(f'Finished command: search')


# -- _parseParamMedicOutput: returns (precursor_ppm, fragment_da) parsed from param-medic output
#    Returns (None, None) if the expected output file is absent or unparseable
def _parseParamMedicOutput(pm_dir: Path):
    import re
    result_file = pm_dir / 'param-medic.txt'
    if not result_file.exists():
        logMsg.warn(f'param-medic output not found {result_file}')
        return None, None
    logMsg.debug(f'Parsing param-medic output {result_file}')
    text = result_file.read_text()
    prec_match = re.search(r'precursor[^\d]+([\d.]+)\s*ppm', text, re.IGNORECASE)
    bin_width_match = re.search(r'fragment[^\d]+([\d.]+)\s*Da', text, re.IGNORECASE)
    prec = float(prec_match.group(1))      if prec_match else None
    bin_width = float(bin_width_match.group(1)) if bin_width_match else None
    logMsg.debug(f'param-medic estimates: precursor {prec} ppm, bin width {bin_width} Da')
    return prec, bin_width

# -- _runParamMedic:
def _runParamMedic(crux_bin, mzml_files, out_dir):
    import statistics
    logMsg.debug(f'Running param-medic across input files')
    prec_estimates, bin_width_estimates = [], []
    pm_out = out_dir.parent / 'param-medic'
    pm_out.mkdir(parents=True, exist_ok=True)
    for mzml_file in mzml_files:
        logMsg.progress(f'param-medic running on {mzml_file.name}')
        file_out = pm_out / mzml_file.stem
        file_out.mkdir(parents=True, exist_ok=False)
        ok = cruxutil.paramMedic(crux_bin, mzml_file, file_out)
        if ok:
            prec, bin_width = _parseParamMedicOutput(file_out)
            if prec is not None:
                prec_estimates.append(prec)
            if bin_width is not None:
                bin_width_estimates.append(bin_width)
    if prec_estimates:
        precursor_tol = statistics.median(prec_estimates)
        logMsg.debug(f'param-medic median precursor tolerance {precursor_tol:.2f} ppm from {len(prec_estimates)} file(s)')
    else:
        precursor_tol = None
        logMsg.warn(f'param-medic produced no usable precursor estimates, using config default')
    if bin_width_estimates:
        mz_bin_width = statistics.median(bin_width_estimates)
        logMsg.info(f'param-medic median fragment bin width {mz_bin_width} Da from {len(bin_width_estimates)} file(s)')
    else:
        mz_bin_width = None
        logMsg.warn(f'param-medic produced no usable bin width estimates, using config default')
    return precursor_tol, mz_bin_width