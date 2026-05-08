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
        console.print(f'[red][bold]{section}[/bold] failed to run: [dim]{result.stderr}[/dim][/red]')
        return False
    console.print(f'[green][bold]{section}[/bold] ran successfully[/green]')
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
    quantify_dir: Path,
    sample_sheet: Path,
    output_dir: Path,
    lfq_dir: Path | None,
    ref_info: Path | None,
    cont_csv: Path | None,
    organism_prefix: str,
    min_reps: int,
    lfc_threshold: float,
    fdr_threshold: float,
    sections: list[str],
    overwrite: bool,
    rscript: str,
    in_pipeline: bool
) -> None:
    if not in_pipeline:
        log = logMsg('report')
        log.debug('Starting report command')
    # Validate inputs
    sc_files = list(quantify_dir.glob('*.spectral-counts.target.txt'))
    if not sc_files:
        print(f'[bold red]ERROR:[/bold red] no spectral count quantification output files found in {quantify_dir}')
        logMsg.error(f'No spectral count quantification output files found in {quantify_dir}')
        raise SystemExit(1)
    try:
        loadSampleSheet(sample_sheet)
    except ValueError as e:
        print(f'[bold red]ERROR:[/bold red] {e}')
        logMsg.error(f'Error loading sample sheet: {e}')
        raise SystemExit(1)
    if ref_info is not None and not ref_info.is_file():
        print(f'[bold red]ERROR:[/bold red] --ref-info path {ref_info} not found')
        logMsg.error(f'--ref-into path {ref_info} not found')
        raise SystemExit(1)
    if cont_csv is not None and not cont_csv.is_file():
        print(f'[bold red]ERROR:[/bold red] --cont-csv path {cont_csv} not found')
        logMsg.error(f'--cont-csv path {cont_csv} not found')
        raise SystemExit(1)
    if output_dir.exists() and not overwrite:
        print(f'[bold red]ERROR:[/bold red] Output directory {output_dir} already exists, use --overwrite')
        logMsg.error(f'Output directory {output_dir} already exists')
        raise SystemExit(1)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Drop concordance if no LFQ data
    if 'concordance' in sections and lfq_dir is None:
        print('[dim]No --lfq-dir provided: skipping concordance section[/dim]')
        sections = [s for s in sections if s != 'concordance']
    if lfq_dir is not None and not lfq_dir.is_dir():
        print(f'[bold red]ERROR:[/bold red] --lfq-dir {lfq_dir} not found')
        logMsg.error(f'--lfq-dir {lfq_dir} not found')
        raise SystemExit(1)
    # Check Rscript is available
    if shutil.which(rscript) is None:
        print(f'[bold red]ERROR:[/bold red] Rscript {rscript} not callable')
        logMsg.error(f'Rscript {rscript} not callable')
        raise SystemExit(1)
    # Run command
    logMsg.info(f'Starting report generation with {len(sections)} section(s)')
    print(f'\nStarting report generation with {len(sections)} section(s)\n')
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
    logMsg.info(f'Report completed - {n_ok} succeeded, {n_fail} failed')
    if n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] report generation failed for {n_fail} section(s).')
    print(f'\n[bold green]Report finished successfully - summary:[/]')
    print(f'- Sections written successfully: {n_ok}')
    print(f'- Sections failed: {n_fail}')
    print(f'- Output directory: {output_dir}\n')