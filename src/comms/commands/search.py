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
from comms.utils.settings import config
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_search: runs tide-search on all mzML files in input_dir and writes results to output
def run_search(input_dir: Path, index_dir: Path, output: Path, param_medic: bool, threads: int, in_pipeline: bool = False):
    if not in_pipeline:
        logMsg('search')
    logMsg.debug('Started command: search')
    crux_bin, _ = validate(check_crux=True)
    logMsg.debug(f'Scanning {input_dir }for mzML files')
    mzml_files = sorted(
        list(input_dir.glob('[!.]*.mzML')) + list(input_dir.glob('[!.]*.mzML.gz'))
    )
    if not mzml_files:
        logMsg.error(f'No mzML files found in {input_dir}')
        raise SystemExit(1)
    logMsg.info(f'Searching {len(mzml_files)} mzML file(s)')
    out_dir = pathutil.generateOutputFileStructure(output, 'search')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'search.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    # -- Optional: param-medic tolerance estimation
    precursor_tol = None
    mz_bin_width  = None
    if param_medic:
        logMsg.progress(f'Estimating tolerances with param-medic')
        precursor_tol, mz_bin_width = _runParamMedic(crux_bin=crux_bin, mzml_files=mzml_files, out_dir=out_dir)
    prec_display = precursor_tol or config['search']['precursor_tolerance_ppm']
    bin_width_display = mz_bin_width or config['search']['mz_bin_width']
    logMsg.debug(f'Precursor tolerance {prec_display} ppm, m/z bin width {bin_width_display} Da')
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
                config=config,
                threads=threads,
                precursor_tol=prec_display,
                mz_bin_width=bin_width_display,
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