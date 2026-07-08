'''
comMS experiment functions
'''

# -- Import external dependencies
import re, tomli_w, tomllib, typer
from datetime import datetime, timezone
from pathlib import Path
from rich import print
from typing import Literal

# -- Import internal functions
from comms.commands.config import _apply_protocol_flags, _apply_organism, _writeConfigTo
from comms.utils.context import _normalise_dirs
from comms.utils.log import logMsg
from comms.utils.settings import loadDefaultConfig
from comms.utils.sheet import SampleRow, render_sample_sheet, parse_sample_sheet

# -- _existing_experiment: returns (root, comms_dir, metadata, config, sample_rows) if experiment_dir already holds a saved experiment else None
def _existing_experiment(experiment_dir: Path):
    root, comms_dir = _normalise_dirs(experiment_dir)
    meta_path = comms_dir / 'experiment.toml'
    config_path = comms_dir / 'config.toml'
    if not (meta_path.exists() and config_path.exists()):
        return None
    with meta_path.open('rb') as f:
        metadata = tomllib.load(f)
    with config_path.open('rb') as f:
        config = tomllib.load(f)
    sheet_path = comms_dir / 'sample_sheet.tsv'
    rows: list[SampleRow] = []
    if sheet_path.exists():
        rows = parse_sample_sheet(sheet_path.read_text(encoding='utf-8'))
    return root, comms_dir, metadata, config, rows

# -- launch_experiment_gui: opens the PySide6 experiment setup window
def launch_experiment_gui() -> None:
    logMsg('experiment')
    try:
        from comms.gui.app import run_app
    except ImportError as e:
        logMsg.error(f'Could not import GUI components: {e}')
        raise SystemExit(1)
    logMsg.info(f'Launching experiment setup GUI')
    raise SystemExit(run_app())

# -- _prompt_list: return a list of strings by repeated prompting, prepopulated with any existing items
def _prompt_list(label: str, existing: list[str] | None = None) -> list[str]:
    items: list[str] = list(existing or [])
    if items:
        print(f'Current {label}(s): {", ".join(items)}')
    while True:
        value = typer.prompt(f'Add a {label} (blank to finish)', default='', show_default=False)
        value = value.strip()
        if not value:
            break
        if value not in items:
            items.append(value)
    return items

# -- _choose: prompt until the user picks one of the allowed options, prepopulated with any existing values
def _choose(label: str, options: list[str], default: str | None = None) -> str:
    while True:
        choice = typer.prompt(f'{label} {options}', default=default, show_default=default is not None)
        if choice in options:
            return choice

# -- run_experiment_headless: build a sample sheet, config and metadata via prompts, or edit an existing experiment
def run_experiment_headless(experiment_dir: Path | None = None) -> None:
    logMsg('experiment')
    logMsg.debug('Starting command: experiment')
    existing = _existing_experiment(experiment_dir) if experiment_dir else None
    edit_mode = existing is not None
    if edit_mode:
        root, comms_dir, metadata, config, existing_rows = existing
        logMsg.info(f'Existing experiment found at {comms_dir}, editing in place')
    else:
        metadata, config, existing_rows = {}, {}, []
    logMsg.info('Starting headless experiment edit' if edit_mode else 'Starting headless experiment setup')

    name = typer.prompt(
        'Experiment name',
        default=metadata.get('experiment', {}).get('name', ''), show_default=edit_mode,
    )
    if edit_mode:
        base_dir = root
    else:
        base_dir = Path(typer.prompt('Save experiment to (directory)', default=str(experiment_dir) if experiment_dir else None, show_default=experiment_dir is not None)).expanduser()
    bin_dir = typer.prompt('Bin directory (blank to auto-resolve)', default=metadata.get('experiment', {}).get('bin_dir', ''), show_default=edit_mode).strip()
    database = typer.prompt('Combined database FASTA', default=metadata.get('files', {}).get('database', ''), show_default=edit_mode).strip()
    existing_treatments = sorted({r.treatment for r in existing_rows if r.treatment})
    existing_fractions = sorted({r.fraction for r in existing_rows if r.fraction})
    treatments = _prompt_list('treatment', existing=existing_treatments)
    fractions = _prompt_list('fraction', existing=existing_fractions)
    if not treatments or not fractions:
        logMsg.error('At least one treatment and one fraction are required')
        raise SystemExit(1)

    input_dir = Path(typer.prompt('Directory of .RAW / .mzML files')).expanduser()
    input_files = _prompt_list('data file')
    files = []
    for f in input_files:
        f = Path(Path(f).expanduser())
        if f.name.startswith('.') or f.suffix.lower() not in ('.raw', '.mzml', '.mzml.gz'):
            continue
        files.append(f)
    if not files:
        logMsg.error(f'No .RAW or .mzML files found in {input_dir}')
        raise SystemExit(1)

    existing_by_raw = {r.raw_file: r for r in existing_rows}
    rows: list[SampleRow] = []
    counters: dict[tuple[str, str], int] = {}
    for f in files:
        print(f'\n[bold]{f.name}[/bold]')
        prior = existing_by_raw.get(f.name)
        treatment = _choose('Treatment', treatments, default=prior.treatment if prior else None)
        fraction = _choose('Fraction', fractions, default=prior.fraction if prior else None)
        key = (treatment, fraction)
        counters[key] = counters.get(key, 0) + 1
        rows.append(SampleRow(
            sample_id=prior.sample_id if prior else f.stem, 
            raw_file=f.name,
            treatment=treatment,
            fraction=fraction,
            replicate=counters[key],
        ))

    # Config: reuse the same helpers as the GUI's ConfigPanel
    index_cfg = config.get('index', {})
    search_cfg = config.get('search', {})
    cfg = loadDefaultConfig()
    cfg = _apply_protocol_flags(
        cfg,
        iodo=typer.confirm('Cysteine carbamidomethylation (static)?', default='C+0' not in index_cfg.get('fixed_mods', '')),
        ox=typer.confirm('Methionine oxidation (variable)?', default=bool(re.search(r'M\+15\.9949', index_cfg.get('mods_spec', ''))) if edit_mode else True),
        phos=typer.confirm('STY phosphorylation (variable)?', default=bool(re.search(r'STY\+79\.966331', index_cfg.get('mods_spec', ''))) if edit_mode else False),
        n_cyc=typer.confirm('N-terminal Gln cyclisation?', default=bool(index_cfg.get('nterm_peptide_mods_spec', '')) if edit_mode else True),
        n_ace=typer.confirm('Protein N-terminal acetylation?', default=bool(index_cfg.get('nterm_protein_mods_spec', '')) if edit_mode else True),
        clip_met=typer.confirm('Clip N-terminal methionine?', default=index_cfg.get('clip_n_met', True) if edit_mode else True),
        low_res=typer.confirm('Low-resolution instrument (ion trap)?', default=(search_cfg.get('score_function') == 'combined-p-value') if edit_mode else False),
    )
    cfg.setdefault('index', {})['custom_mods'] = index_cfg.get('custom_mods', '')
    organisms: dict[str, str] = dict(config.get('organism', {})) if edit_mode else {}
    multispecies = typer.confirm('Multispecies analysis (per-organism FDR)?', default=bool(organisms))
    if multispecies:
        while True:
            label = typer.prompt('Organism label (blank to finish)', default='', show_default=False).strip()
            if not label:
                break
            pattern = typer.prompt(f'Header pattern for {label}').strip()
            if pattern:
                organisms[label] = pattern
    else:
        organisms = {}
    cfg = _apply_organism(cfg, organisms)
    if multispecies:
        cfg['percolator']['shared_psm'] = typer.prompt('Shared PSM handling policy', default=config.get('percolator', {}).get('shared_psm', 'drop'), type=Literal['drop', 'include'], show_choices=True, show_default=True).strip()
    report_meta = metadata.get('report', {})
    organism_prefix = ''
    include_report = typer.confirm('Create report?', default=report_meta.get('enabled', True))
    if include_report:
        reference = typer.prompt('Reference protein annotation file (blank to skip)', default=report_meta.get('ref_info', ''), show_default=edit_mode).strip()
        contaminants = typer.prompt('Contaminants list CSV path (blank to skip)', default=report_meta.get('cont_csv', ''), show_default=edit_mode).strip()
        if multispecies:
            organism_prefix = typer.prompt('Primary organism ID prefix', default=report_meta.get('organism_prefix', ''), show_default=edit_mode).strip()
        status = rdepsFuncs.check_r_dependencies()
        if status is not None and status['missing']:
            if typer.confirm(f"Install missing R report dependencies now? ({', '.join(status['missing'])})", default=True):
                rdepsFuncs.install_r_dependencies()

    # Write all three files
    out_dir = base_dir / 'comms'
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = out_dir / 'sample_sheet.tsv'
    sheet_path.write_text(render_sample_sheet(rows), encoding='utf-8')
    config_path = out_dir / 'config.toml'
    _writeConfigTo(cfg, config_path)
    meta = {'experiment': {
        'name': name,
        'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }}
    if bin_dir:
        meta['experiment']['bin_dir'] = bin_dir
    meta['files'] = {
        'sample_sheet': str(sheet_path),
        'config': str(config_path),
        'database': database,
        'data': [str(f) for f in files],
    }
    if multispecies:
        meta['experiment']['analysis_mode'] = 'multi'
    if include_report:
        meta.setdefault('report', {})['enabled'] = True
        if reference != '':
            meta['report']['ref_info'] = reference
        if contaminants != '':
            meta['report']['cont_csv'] = contaminants
        if multispecies and organism_prefix != '':
            meta['report']['organism_prefix'] = organism_prefix
    else:
        meta.setdefault('report', {})['enabled'] = False
    with (out_dir / 'experiment.toml').open('wb') as f:
        tomli_w.dump(meta, f)
    logMsg.info(f'Experiment {"updated" if edit_mode else "written"} at {out_dir}')
    print(f'\nRun the pipeline with:\n'
          f'\t[bold]comms pipeline {sheet_path} --database <db.fasta> --input {input_dir} --experiment-dir {base_dir}[/bold]\n')