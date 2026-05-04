'''
comMS search functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_search: runs tide-search on all mzML files in input_dir and writes results to output
def run_search(input_dir: Path, index_dir: Path, output: Path, param_medic: bool, threads: int, in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('search')
        log.debug('Starting search command')
    logMsg.debug('Locating Crux binary')
    bin_dir = pathutil.repoBinDir()
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        logMsg.error(f'Crux binary not found under: {bin_dir}')
        raise SystemExit(1)
    logMsg.debug(f'Scanning for mzML files in: {input_dir}')
    mzml_files = sorted(
        list(input_dir.glob('*.mzML')) + list(input_dir.glob('*.mzML.gz'))
    )
    if not mzml_files:
        logMsg.warn(f'No mzML files found in: {input_dir}')
        raise SystemExit(1)
    logMsg.info(f'Found {len(mzml_files)} mzML file(s) — starting search')
    out_dir = pathutil.generateOutputFileStructure(output, 'search')
    log_path = out_dir / 'search.log'
    # -- Optional: param-medic tolerance estimation
    precursor_tol = None
    mz_bin_width  = None
    if param_medic:
        logMsg.info(f'Running param-medic on: {mzml_files[0].name}')
        pm_out = out_dir.parent / 'param-medic'
        pm_out.mkdir(parents=True, exist_ok=True)
        ok = cruxutil.paramMedic(crux_bin, mzml_files[0], pm_out, log_path)
        if ok:
            precursor_tol, mz_bin_width = _parseParamMedicOutput(pm_out)
        if precursor_tol is None:
            logMsg.warn('param-medic produced no usable output — falling back to config defaults')
    prec_display = precursor_tol or config['search']['precursor_tolerance_ppm']
    bin_width_display = mz_bin_width or config['search']['mz_bin_width']
    logMsg.debug(f'Using precursor tolerance: {prec_display} ppm, m/z bin width: {bin_width_display}')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for mzml_file in tqdm(mzml_files, desc='Files searched'):
            fileroot = mzml_file.name.removesuffix('.gz').removesuffix('.mzML')
            ok = cruxutil.tideSearch(
                crux_bin=crux_bin,
                mzml_file=mzml_file,
                index_dir=index_dir,
                out_dir=out_dir,
                fileroot=fileroot,
                config=config,
                precursor_tol=prec_display,
                mz_bin_width=bin_width_display,
            )
            if ok:
                n_ok += 1
            else:
                logMsg.warn(f'Tide-search failed for: {mzml_file.name}')
                n_fail += 1
    logMsg.info(f'Complete — {n_ok} succeeded, {n_fail} failed')
    if n_fail > 0:
        logMsg.warn(f'Quantification failed for {n_fail} files(s). Check {log_path} for details.')
    print(f'\n[bold green]Search finished successfully - summary:[/]')
    print(f'- Search parameters: {prec_display} precursor tolerance; {bin_width_display} m/z bin width')
    print(f'- Files searched successfully: {n_ok}')
    print(f'- Files failed: {n_fail}')
    print(f'- Output directory: {out_dir}\n')


# -- _parseParamMedicOutput: returns (precursor_ppm, fragment_da) parsed from param-medic output
#    Returns (None, None) if the expected output file is absent or unparseable
def _parseParamMedicOutput(pm_dir: Path):
    import re
    result_file = pm_dir / 'param-medic.txt'
    if not result_file.exists():
        logMsg.warn(f'param-medic output file not found at: {result_file}')
        return None, None
    logMsg.debug(f'Parsing param-medic output from: {result_file}')
    text = result_file.read_text()
    prec_match = re.search(r'precursor[^\d]+([\d.]+)\s*ppm', text, re.IGNORECASE)
    bin_width_match = re.search(r'fragment[^\d]+([\d.]+)\s*Da', text, re.IGNORECASE)
    prec = float(prec_match.group(1))      if prec_match else None
    bin_width = float(bin_width_match.group(1)) if bin_width_match else None
    logMsg.debug(f'param-medic result — precursor: {prec} ppm, bin width: {bin_width} Da')
    return prec, bin_width