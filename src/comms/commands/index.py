'''
comMS index functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.context import ExperimentContext, resolve_database
from comms.utils.modspec import apply_protocol_flags, apply_custom_mod
from comms.utils.settings import _writeConfigTo
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

def run_index(
    database, 
    ctx: ExperimentContext,
    in_pipeline: bool = False,
    iodo=None,
    ox=None,
    phos=None,
    n_cyc=None,
    n_ace=None,
    custom=None,
    clip_met=None,
    missed_cleavages=None,
):
    if not in_pipeline:
        logMsg('index')
    logMsg.debug('Started command: index')
    crux_bin, _ = validate(check_crux=True, bin_dir=ctx.bin_dir)
    database = resolve_database(ctx, database)
    logMsg.info(f'Indexing database {database.name}')
    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'index')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'index.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    # Build a config for this run only if any override was given
    overrides_given = any(v is not None for v in (iodo, ox, phos, n_cyc, n_ace, custom, clip_met, missed_cleavages))
    if overrides_given:
        logMsg.debug('Using run-specific configuration parameters')
        run_config = {**ctx.config, 'index': dict(ctx.config.get('index', {}))}
        run_config = apply_protocol_flags(
            run_config,
            iodo=iodo,
            ox=ox,
            phos=phos,
            n_cyc=n_cyc,
            n_ace=n_ace,
            clip_met=clip_met,
            missed_cleavages=missed_cleavages,
        )
        if custom is not None:
            current = run_config['index'].get('custom_mods', '')
            run_config['index']['custom_mods'] = apply_custom_mod(current, custom)
        logMsg.info('Command-line overrides detected - run configuration file will be saved to output folder as "index.config.toml"')
        _writeConfigTo(run_config, path=Path(out_dir, 'index.config.toml'))
    else:
        logMsg.debug('Using contextual configuration parameters')
        run_config = ctx.config
    logMsg.progress(f'Building Tide peptide index')
    ok = cruxutil.tideIndex(
        crux_bin=crux_bin,
        database=database,
        index_dir=out_dir,
        config=run_config,
    )
    if not ok:
        logMsg.error(f'tide-index failed, see {log_path}')
        raise SystemExit(1)
    logMsg.info(f'Indexing complete: peptide index saved to {out_dir}')
    logMsg.debug(f'Finished command: index')