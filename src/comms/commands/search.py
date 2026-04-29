'''
comMS search functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.settings import config, lg
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_search: runs tide-search on all mzML files in input_dir and writes results to output
def run_search(input_dir: Path, index_dir: Path, output: Path, param_medic: bool, threads: int):
    lg.debug('search | Locating Crux binary...')
    bin_dir = pathutil.repoBinDir()
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        print(f'[bold red]ERROR:[/bold red] Crux binary not found under {bin_dir}.')
        raise SystemExit(1)
    mzml_files = sorted(
        list(input_dir.glob('*.mzML')) + list(input_dir.glob('*.mzML.gz'))
    )
    if not mzml_files:
        print(f'[bold red]ERROR:[/bold red] No mzML files found in {input_dir}.')
        raise SystemExit(1)
    out_dir = pathutil.generateOutputFileStructure(output, 'search')
    log_path = out_dir.parent / 'search.log'
    # -- Optional: param-medic tolerance estimation
    precursor_tol = None
    fragment_tol = None
    if param_medic:
        lg.info('search | Running param-medic on first mzML file...')
        print('Running param-medic to estimate mass tolerances...')
        pm_out = out_dir.parent / 'param-medic'
        pm_out.mkdir(parents=True, exist_ok=True)
        ok = cruxutil.paramMedic(crux_bin, mzml_files[0], pm_out, log_path)
        if ok:
            precursor_tol, fragment_tol = _parseParamMedicOutput(pm_out)
        if precursor_tol is None:
            print(f'[bold yellow]WARNING:[/bold yellow] param-medic did not produce usable output — using config defaults.')
    prec_display = precursor_tol or config['search']['precursor_tolerance_ppm']
    frag_display = fragment_tol or config['search']['fragment_tolerance_da']
    print(f'\nRunning Tide-search on {len(mzml_files)} file(s)...')
    print(f'- Precursor tolerance: {prec_display} ppm')
    print(f'- Fragment tolerance: {frag_display} Da')
    print(f"- Score function: {config['search']['score_function']}")
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
                precursor_tol=precursor_tol,
                fragment_tol=fragment_tol,
                log_path=log_path,
            )
            if ok:
                n_ok += 1
            else:
                lg.warning(f'search | Tide-search failed for {mzml_file.name}.')
                n_fail += 1

    print(f'\n[bold]Search summary[/bold]')
    print(f'- Files searched successfully: {n_ok}')
    print(f'- Files failed: {n_fail}')
    print(f'- Output directory: {out_dir}\n')


# -- _parseParamMedicOutput: returns (precursor_ppm, fragment_da) parsed from param-medic output
#    Returns (None, None) if the expected output file is absent or unparseable
def _parseParamMedicOutput(pm_dir: Path):
    import re
    result_file = pm_dir / 'param-medic.txt'
    if not result_file.exists():
        return None, None
    text = result_file.read_text()
    prec_match = re.search(r'precursor[^\d]+([\d.]+)\s*ppm', text, re.IGNORECASE)
    frag_match  = re.search(r'fragment[^\d]+([\d.]+)\s*Da',  text, re.IGNORECASE)
    prec = float(prec_match.group(1)) if prec_match else None
    frag = float(frag_match.group(1)) if frag_match else None
    return prec, frag