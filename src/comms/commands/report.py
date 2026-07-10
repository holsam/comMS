'''
comMS report functions
'''

# -- Import external dependencies
import json, shutil, subprocess, sys
from datetime import datetime
from importlib.resources import files as pkg_files
from pathlib import Path
from rich import print
from rich.console import Console

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.samples import loadSampleSheet
from comms.utils.settings import resolve_config_value, _writeConfigTo
from comms.utils.context import ExperimentContext, resolve_organism_prefix, resolve_sample_sheet, resolve_results_input, results_dir

# -- Initialise Rich console
console = Console()

# -- Define helper dictionary matching sections to R scripts, LFQ requirement, and whether the section reports per-organism status
_SECTIONS: dict[str, tuple[str, bool, bool]] = {
    # Core sections: (script, needs_lfq, per_organism)
    'qc': ('qc.R', False, True),
    'pca': ('pca.R', False, True),
    'da': ('da.R', False, True),
    'secondary-species': ('secondary-species.R', False, False),
    'concordance': ('concordance.R', True, True),
    # Auxiliary sections
    'ev-markers': ('aux/ev-markers.R', False, True),
}

# -- Define helper dictionary for potential per-organism section statuses
_ORGANISM_STATUSES = {'ok', 'skipped', 'failed'}

# -- _resolve_r_script: returns Path to R script
def _resolve_r_script(script_name: str) -> Path:
    '''Locate R script based on provided script name'''
    return pkg_files('comms').joinpath(f'r/sections/{script_name}')

# -- _read_status: returns tuple of dicts (containing organisms, reasons) parsed from a section's _status.json
def _read_status(output_subdir: Path) -> tuple[dict[str, str], dict[str, str]]:
    status_path = output_subdir / '_status.json'
    if not status_path.exists():
        return {}, {}
    try:
        payload = json.loads(status_path.read_text())
    except Exception as e:
        logMsg.debug(f'Could not parse {status_path}: {e}')
        return {}, {}
    organisms = {k: v for k, v in payload.get('organisms', {}).items() if v in _ORGANISM_STATUSES}
    reasons = dict(payload.get('reasons', {}))
    return organisms, reasons

# -- _section_status: returns string (either 'succeeded', 'partial', 'failed' or 'skipped')
def _section_status(proc_ok: bool, organisms: dict[str, str]) -> str:
    if not organisms:
        # No structured status available (legacy/non-organism script, or crash before writing status)
        return 'failed' if not proc_ok else 'skipped'
    ok = sum(1 for s in organisms.values() if s == 'ok')
    failed = sum(1 for s in organisms.values() if s == 'failed')
    if failed == 0:
        return 'succeeded' if ok > 0 else 'skipped'
    return 'partial' if ok > 0 else 'failed'

# -- _log_organism_outcomes: returns None but outputs logging messages
def _log_organism_outcomes(section: str, organisms: dict[str, str], reasons: dict[str, str]) -> None:
    for org, status in organisms.items():
        reason = reasons.get(org)
        suffix = f' ({reason})' if reason else ''
        if status == 'ok':
            logMsg.progress(f'{section} — {org}: succeeded')
        elif status == 'skipped':
            logMsg.progress(f'{section} — {org}: skipped{suffix}')
        else:
            logMsg.progress(f'{section} — {org}: failed{suffix}')

# -- _run_r_section: returns boolean indicating if the R process itself exited cleanly
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
def _write_index(
        output_dir: Path,
        params: dict,
        section_status: dict[str, str],
        organism_results: dict[str, dict[str, str]],
) -> None:
    lines = [
        '# comms report',
        f'\nGenerated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'\n## Parameters\n',
    ]
    for k,v in params.items():
        lines.append(f'- **{k}**: `{v}`')
    lines.append(f'\n## Sections\n')
    status_glyphs = {
        'succeeded': '✓ SUCCEEDED',
        'partial': '◐ PARTIAL',
        'failed': '✗ FAILED',
        'skipped': '- SKIPPED',
    }
    for sec, status in section_status.items():
        lines.append(f'- {sec}: {status_glyphs[status]}')
        for org, org_status in organism_results.get(sec, {}).items():
            lines.append(f'  - {org}: {org_status}')
    (output_dir / 'index.md').write_text('\n'.join(lines))

# -- run_report: return None, but run report section R scripts and output script
def run_report(
        quantify_dir: Path | None,
        sample_sheet: Path | None,
        ctx: ExperimentContext | None,
        lfq_dir: Path | None,
        ref_info: Path | None,
        cont_csv: Path | None,
        organism_prefix: str | None,
        min_reps: int | None,
        lfc_threshold: float | None,
        fdr_threshold: float | None,
        top_n: int | None,
        sections: list,
        overwrite: bool,
        rscript: str,
        in_pipeline: bool,
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

    # Build config for this run only if any override was given
    overrides_given = any(v is not None for v in (min_reps, lfc_threshold, fdr_threshold, top_n))
    if overrides_given:
        logMsg.debug('Using run-specific configuration parameters')
        run_config = {**ctx.config, 'report': dict(ctx.config.get('report', {}))}
        run_config['report']['min_reps'] = resolve_config_value(ctx.config, 'report', 'min_reps', min_reps)
        run_config['report']['lfc_threshold'] = resolve_config_value(ctx.config, 'report', 'lfc_threshold', lfc_threshold)
        run_config['report']['fdr_threshold'] = resolve_config_value(ctx.config, 'report', 'fdr_threshold', fdr_threshold)
        run_config['report']['top_n_proteins'] = resolve_config_value(ctx.config, 'report', 'top_n_proteins', top_n)
        logMsg.info('Command-line overrides detected - run configuration file will be saved to output folder as "report.config.toml"')
        _writeConfigTo(run_config, path=Path(out_dir, 'report.config.toml'))
    else:
        logMsg.debug('Using contextual configuration parameters')
        run_config = ctx.config

    # Run command
    logMsg.info(f'Generating report: {len(sections)} section(s)')
    # Define arguments passed to every R script
    common_args = [
        str(quantify_dir),
        str(sample_sheet),
        str(ref_info) if ref_info else '',
        str(cont_csv) if cont_csv else '',
        organism_prefix,
        str(run_config['report']['min_reps']),
    ]
    section_status: dict[str, str] = {}
    organism_results: dict[str, dict[str, str]] = {}
    for sec in sections:
        logMsg.progress(f'Running section: {sec}')
        script, needs_lfq, per_organism = _SECTIONS[sec]
        extra: list[str] = []
        if sec == 'da':
            extra = [str(run_config['report']['lfc_threshold']), str(run_config['report']['fdr_threshold']), str(run_config['report']['top_n_proteins'])]
        elif sec == 'concordance':
            extra = [str(lfq_dir), str(run_config['report']['lfc_threshold']), str(run_config['report']['fdr_threshold'])]
        output_subdir = output_dir / sec.replace('-', '_')
        proc_ok = _run_r_section(
            section = sec,
            script_name=script,
            output_subdir=output_subdir,
            positional_args=common_args+extra,
            rscript=rscript,
        )
        organisms, reasons = _read_status(output_subdir) if per_organism else ({}, {})
        section_status[sec] = _section_status(proc_ok, organisms)
        organism_results[sec] = organisms
        if organisms:
            _log_organism_outcomes(sec, organisms, reasons)

    _write_index(
        output_dir,
        {
            'quantify_dir': quantify_dir,
            'sample_sheet': sample_sheet,
            'lqf_dir': lfq_dir or 'not provided',
            'organism_prefix': organism_prefix,
            'min_reps': run_config['report']['min_reps'],
            'lfc_threshold': run_config['report']['lfc_threshold'],
            'fdr_threshold': run_config['report']['fdr_threshold'],
            'top_n_proteins': run_config['report']['top_n_proteins'],
        },
        section_status,
        organism_results,
    )

    n_succeeded = sum(1 for s in section_status.values() if s == 'succeeded')
    n_partial = sum(1 for s in section_status.values() if s == 'partial')
    n_failed = sum(1 for s in section_status.values() if s == 'failed')
    n_skipped = sum(1 for s in section_status.values() if s == 'skipped')
    parts = [f'{n_succeeded} succeeded']
    if n_partial:
        parts.append(f'{n_partial} partial (at least one organism failed)')
    if n_failed:
        parts.append(f'{n_failed} failed')
    if n_skipped:
        parts.append(f'{n_skipped} skipped (no organism had sufficient data)')
    logMsg.info(f'Report complete: {", ".join(parts)}')
    logMsg.debug(f'Finished command: report')