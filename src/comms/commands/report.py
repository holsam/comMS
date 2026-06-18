'''
comMS report functions
'''

# -- Import external dependencies
import shutil, subprocess, sys
from datetime import datetime
from importlib.resources import files as pkg_files
from pathlib import Path
from rich import print
from rich.console import Console

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.samples import loadSampleSheet
from comms.utils.context import ExperimentContext, resolve_organism_prefix, resolve_sample_sheet, resolve_results_input, results_dir

# -- Initialise Rich console
console = Console()

# -- Define helper dictionary matching sections to R scripts and whether they require LFQ data
_SECTIONS: dict[str, tuple[str, bool]] = {
    # Core sections
    'qc': ('qc.R', False),
    'pca': ('pca.R', False),
    'da': ('da.R', False),
    'secondary-species': ('secondary-species.R', False),
    'concordance': ('concordance.R', True),
    # Auxiliary sections
    'ev-markers': ('aux/ev-markers.R', False),
}

# -- _resolve_r_script: returns Path to R script
def _resolve_r_script(script_name: str) -> Path:
    '''Locate R script based on provided script name'''
    return pkg_files('comms').joinpath(f'r/sections/{script_name}')

# -- _run_r_script: returns boolean indicating if command was run successfully
def _run_r_section(
        section: str,
        script_name: str,
        output_subdir: Path,
        positional_args: list[str],
        rscript: str,
) -> bool:
    '''Invoke a single R script'''
    script_path = _resolve_r_script(script_name)
    output_subdir.mkdir(parents=True, exist_ok=True)
    cmd = [rscript, '--vanilla', str(script_path), str(output_subdir)] + positional_args
    logMsg.debug(f'Running {section}: {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logMsg.warn(f'Section {section} failed: {result.stderr}')
        return False
    logMsg.debug(f'Section {section} completed')
    return True

# -- _write_index: return none, but write index
def _write_index(output_dir: Path, params: dict, results: dict[str, bool]) -> None:
    lines = [
        '# comms report',
        f'\nGenerated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'\n## Parameters\n',
    ]
    for k,v in params.items():
        lines.append(f'- **{k}**: `{v}`')
    lines.append(f'\n## Sections\n')
    for sec, ok in results.items():
        status = '✓ SUCCEEDED' if ok else '✗ FAILED'
        lines.append(f'- {sec}: {status}')
    (output_dir / 'index.md').write_text('\n'.join(lines))

# -- run_report: return None, but run report section R scripts and output script
def run_report(
        quantify_dir,
        sample_sheet,
        ctx: ExperimentContext,
        lfq_dir,
        ref_info,
        cont_csv,
        organism_prefix,
        min_reps,
        lfc_threshold,
        fdr_threshold,
        sections,
        overwrite,
        rscript,
        in_pipeline,
    ) -> None:
    if not in_pipeline:
        logMsg('report')
    logMsg.debug('Started command: report')
    # Create path to output_dir
    output_dir = ctx.root / 'comms/results/report'

    # Required inputs resolved from the experiment context
    quantify_dir = resolve_results_input(ctx, 'quantify', quantify_dir)
    sample_sheet = resolve_sample_sheet(ctx, sample_sheet)
    organism_prefix = resolve_organism_prefix(ctx, organism_prefix)

    # Optional inputs: fall back to stored values, then to the conventional lfq directory
    ref_info = ref_info or ctx.ref_info
    cont_csv = cont_csv or ctx.cont_csv
    if lfq_dir is None:
        default_lfq_dir = results_dir(ctx, 'lfq')
        if default_lfq_dir.exists():
            lfq_dir = default_lfq_dir
    # Validate inputs
    sc_files = list(quantify_dir.glob('[!.]*.spectral-counts.target.txt'))
    if not sc_files:
        logMsg.error(f'No quantification output files found in {quantify_dir}')
        raise SystemExit(1)
    try:
        loadSampleSheet(sample_sheet)
    except ValueError as e:
        logMsg.error(f'Could not load sample sheet: {e}')
        raise SystemExit(1)
    if ref_info is not None and not Path(ref_info).is_file():
        logMsg.error(f'--ref-info not found: {ref_info}')
        raise SystemExit(1)
    if cont_csv is not None and not Path(cont_csv).is_file():
        logMsg.error(f'--cont-csv not found: {cont_csv}')
        raise SystemExit(1)
    if output_dir.exists() and not overwrite:
        logMsg.error(f'Output directory already exists: {output_dir}')
        raise SystemExit(1)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Drop concordance if no LFQ data
    if 'concordance' in sections and lfq_dir is None:
        logMsg.warn('No --lfq-dir provided, skipping concordance section')
        sections = [s for s in sections if s != 'concordance']
    if lfq_dir is not None and not Path(lfq_dir).is_dir():
        logMsg.error(f'--lfq-dir not found: {lfq_dir}')
        raise SystemExit(1)
    # Check Rscript is available
    if shutil.which(rscript) is None:
        logMsg.error(f'Rscript not callable: {rscript}')
        raise SystemExit(1)
    # Run command
    logMsg.info(f'Generating report: {len(sections)} section(s)')
    # Define arguments passed to every R script
    common_args = [
        str(quantify_dir),
        str(sample_sheet),
        str(ref_info) if ref_info else '',
        str(cont_csv) if cont_csv else '',
        organism_prefix,
        str(min_reps),
    ]
    results: dict[str, bool] = {}
    for sec in sections:
        logMsg.progress(f'Running section: {sec}')
        script, needs_lfq = _SECTIONS[sec]
        extra: list[str] = []
        if sec == 'da':
            extra = [str(lfc_threshold), str(fdr_threshold)]
        elif sec == 'concordance':
            extra = [str(lfq_dir), str(lfc_threshold), str(fdr_threshold)]
        results[sec] = _run_r_section(
            section = sec,
            script_name=script,
            output_subdir=output_dir / sec.replace('-', '_'),
            positional_args=common_args+extra,
            rscript=rscript,
        )
    _write_index(
        output_dir,
        {
            'quantify_dir': quantify_dir,
            'sample_sheet': sample_sheet,
            'lqf_dir': lfq_dir or 'not provided',
            'organism_prefix': organism_prefix,
            'min_reps': min_reps,
            'lfc_threshold': lfc_threshold,
            'fdr_threshold': fdr_threshold,
        },
        results)
    n_ok = sum(results.values())
    n_fail = len(results) - n_ok
    logMsg.info(f'Report complete: {n_ok} succeeded, {n_fail} failed')
    logMsg.debug(f'Finished command: report')