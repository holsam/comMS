'''
comMS wrapper around Crux binary
'''

# -- Import external dependencies
import subprocess
from pathlib import Path
from typing import Optional

# -- Import internal functions
from comms.utils.settings import lg

# -- findCrux: returns a Path to the Crux binary under bin_dir/crux*/bin/crux, or None if not found
def findCrux(bin_dir: Path) -> Optional[Path]:
    matches = list(bin_dir.glob('crux*/bin/crux'))
    if not matches:
        return None
    return sorted(matches)[-1]

# -- runCrux: returns True if the Crux subcommand completed successfully, False on failure
def runCrux(
    crux_bin: Path,
    subcommand: str,
    args: list,
    log_path: Optional[Path] = None,
) -> bool:
    cmd = [str(crux_bin), subcommand] + [str(a) for a in args]
    lg.debug(f"crux | Running: {' '.join(cmd)}")

    log_fh = open(log_path, 'a') if log_path else subprocess.DEVNULL
    try:
        result = subprocess.run(cmd, stdout=log_fh, stderr=log_fh, check=False)
        if result.returncode != 0:
            lg.warning(f'crux | {subcommand} exited with code {result.returncode}.')
            return False
        return True
    except Exception as e:
        lg.error(f'crux | Unexpected error running {subcommand}: {e}')
        return False
    finally:
        if log_path:
            log_fh.close()

# -- tideIndex: returns True if the Tide peptide index was built successfully, False on failure
def tideIndex(crux_bin, database, index_dir, config, log_path=None):
    args = [
        '--verbosity', '40',
        '--memory-limit', '8',
        '--enzyme', 'trypsin',
        '--digestion', 'full-digest',
        '--missed-cleavages', str(config['search']['missed_cleavages']),
        '--mods-spec', config['search']['mods_spec'],
        '--nterm-peptide-mods-spec', config['search']['nterm_peptide_mods_spec'],
        '--nterm-protein-mods-spec', config['search']['nterm_protein_mods_spec'],
        '--decoy-format', 'peptide-reverse',
        '--num-decoys-per-target', '1',
        '--allow-dups', 'T',
        '--clip-nterm-methionine', 'T',
        '--output-dir', str(index_dir),
        str(database),
        'comms-combined',
    ]
    return runCrux(crux_bin, 'tide-index', args, log_path)

# -- paramMedic: returns True if param-medic completed successfully, False on failure
def paramMedic(crux_bin, mzml_file, out_dir, log_path=None):
    args = [
        '--verbosity', '40',
        '--output-dir', str(out_dir),
        str(mzml_file),
    ]
    return runCrux(crux_bin, 'param-medic', args, log_path)

# -- tideSearch: returns True if Tide-search completed successfully for the given mzML file, False on failure
def tideSearch(crux_bin, mzml_file, index_dir, out_dir, fileroot, config,
               precursor_tol=None, fragment_tol=None, log_path=None):
    prec = precursor_tol or config['search']['precursor_tolerance_ppm']
    frag = fragment_tol or config['search']['fragment_tolerance_da']
    args = [
        '--verbosity', '40',
        '--num-threads', str(config['search']['threads']),
        '--spectrum-parser', 'pwiz',
        '--precursor-window', str(prec),
        '--precursor-window-type', 'ppm',
        '--fragment-mass-tolerance', str(frag),
        '--score-function', config['search']['score_function'],
        '--min-peaks', str(config['search']['min_peaks']),
        '--missed-cleavages', str(config['search']['missed_cleavages']),
        '--output-dir', str(out_dir),
        '--fileroot', fileroot,
        str(mzml_file),
        str(index_dir),
    ]
    return runCrux(crux_bin, 'tide-search', args, log_path)

# -- percolator: returns True if Percolator rescoring completed successfully, False on failure
def percolator(crux_bin, target_psm_file, database, out_dir, fileroot, config, log_path=None):
    args = [
        '--verbosity', '40',
        '--protein', 'T',
        '--protein-enzyme', config['percolator']['protein_enzyme'],
        '--spectral-counting-fdr', str(config['percolator']['psm_fdr']),
        '--min-peptides-per-protein', str(config['percolator']['min_peptides_per_protein']),
        '--output-dir', str(out_dir),
        '--fileroot', fileroot,
        str(target_psm_file),
    ]
    if config['percolator']['picked_protein']:
        args = ['--picked-protein', str(database)] + args
    return runCrux(crux_bin, 'percolator', args, log_path)

# -- spectralCounts: returns True if dNSAF spectral counting completed successfully, False on failure
def spectralCounts(crux_bin, psm_file, database, out_dir, fileroot, config, log_path=None):
    args = [
        '--verbosity', '40',
        '--measure', config['quantify']['measure'],
        '--threshold', str(config['quantify']['qvalue_threshold']),
        '--threshold-type', 'qvalue',
        '--unique-mapping', 'T' if config['quantify']['unique_mapping'] else 'F',
        '--protein-database', str(database),
        '--output-dir', str(out_dir),
        '--fileroot', fileroot,
        str(psm_file),
    ]
    return runCrux(crux_bin, 'spectral-counts', args, log_path)