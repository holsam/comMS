'''
comMS experiment functions
'''

# -- Import external dependencies
import tomli_w, typer
from datetime import datetime, timezone
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.sheet import SampleRow, render_sample_sheet
from comms.commands.config import _apply_protocol_flags, _apply_organism, _writeConfigTo
from comms.utils.settings import loadDefaultConfig

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

# -- _prompt_list: return a list of strings by repeated prompting
def _prompt_list(label: str) -> list[str]:
    items: list[str] = []
    while True:
        value = typer.prompt(f'Add a {label} (blank to finish)', default='', show_default=False)
        value = value.strip()
        if not value:
            break
        if value not in items:
            items.append(value)
    return items

# -- _choose: prompt until the user picks one of the allowed options
def _choose(label: str, options: list[str]) -> str:
    while True:
        choice = typer.prompt(f'{label} {options}')
        if choice in options:
            return choice

# -- run_experiment_headless: build a sample sheet, config and metadata via prompts
def run_experiment_headless() -> None:
    logMsg('experiment')
    logMsg.debug('Starting command: experiment')
    logMsg.info('Starting headless experiment setup')

    name = typer.prompt('Experiment name')
    base_dir = Path(typer.prompt('Save experiment to (directory)')).expanduser()
    bin_dir = typer.prompt('Bin directory (blank to auto-resolve)', default='', show_default=False).strip()
    database = typer.prompt('Combined database FASTA').strip()

    treatments = _prompt_list('treatment')
    fractions = _prompt_list('fraction')
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

    rows: list[SampleRow] = []
    counters: dict[tuple[str, str], int] = {}
    for f in files:
        print(f'\n[bold]{f.name}[/bold]')
        treatment = _choose('Treatment', treatments)
        fraction = _choose('Fraction', fractions)
        key = (treatment, fraction)
        counters[key] = counters.get(key, 0) + 1
        rows.append(SampleRow(
            sample_id=f.stem, raw_file=f.name,
            treatment=treatment, fraction=fraction, replicate=counters[key],
        ))

    # Config: reuse the same helpers as the GUI's ConfigPanel
    cfg = loadDefaultConfig()
    cfg = _apply_protocol_flags(
        cfg,
        iodo=typer.confirm('Cysteine carbamidomethylation (static)?', default=False),
        ox=typer.confirm('Methionine oxidation (variable)?', default=True),
        phos=typer.confirm('STY phosphorylation (variable)?', default=False),
        n_cyc=typer.confirm('N-terminal Gln cyclisation?', default=True),
        n_ace=typer.confirm('Protein N-terminal acetylation?', default=True),
        clip_met=typer.confirm('Clip N-terminal methionine?', default=True),
        low_res=typer.confirm('Low-resolution instrument (ion trap)?', default=False),
    )
    organisms: dict[str, str] = {}
    organism_prefix = ''
    if typer.confirm('Multispecies analysis (per-organism FDR)?', default=False):
        while True:
            label = typer.prompt('Organism label (blank to finish)', default='', show_default=False).strip()
            if not label:
                break
            pattern = typer.prompt(f'Header pattern for {label}').strip()
            if pattern:
                organisms[label] = pattern
        organism_prefix = typer.prompt('Primary organism ID prefix (blank if single species)', default='', show_default=False).strip()
    cfg = _apply_organism(cfg, organisms)
    cfg.setdefault('index', {})['custom_mods'] = ''

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
    if organism_prefix:
        meta.setdefault('report', {})['organism_prefix'] = organism_prefix
    with (out_dir / 'experiment.toml').open('wb') as f:
        tomli_w.dump(meta, f)

    logMsg.info(f'Experiment written to {out_dir}')
    print(f'\nRun the pipeline with:\n'
          f'\t[bold]comms pipeline {sheet_path} --database <db.fasta> --input {input_dir} --experiment-dir {base_dir}[/bold]\n')