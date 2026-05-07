'''
comMS CLI subcommand for managing configuration files
'''

# -- Import external dependencies
import typer
from typing import Annotated, List, Optional

# -- Import internal functions
from comms.commands import config as configFuncs

# -- Initialise config Typer class
commsConfig = typer.Typer(add_completion=False, invoke_without_command=True)

# -- Define config callback
@commsConfig.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        configFuncs.config_exists()

# -- Define config command: init
@commsConfig.command(rich_help_panel='Config Commands')
def init():
    '''Create a user config file with default settings in the OS config directory'''
    configFuncs.config_init()

# -- Define config command: exists
@commsConfig.command(rich_help_panel='Config Commands')
def exists():
    '''Report whether a user config file exists and print its path'''
    configFuncs.config_exists()

# -- Define config command: list
@commsConfig.command(rich_help_panel='Config Commands')
def list():
    '''Print current config values, highlighting differences from bundled defaults'''
    configFuncs.config_list()

# -- Define config command: verify
@commsConfig.command(rich_help_panel='Config Commands')
def verify():
    '''Check that all expected keys are present in the user config file'''
    configFuncs.config_verify()

# -- Define config command: reset
@commsConfig.command(rich_help_panel='Config Commands')
def reset(
    force: Annotated[
        bool,
        typer.Option('--force', help='Skip confirmation and immediately overwrite config.toml')
    ] = False
):
    '''Overwrite the user config file with comMS built-in defaults'''
    configFuncs.config_reset(force=force)

# -- Define config command: set
@commsConfig.command(rich_help_panel='Config Commands')
def set(
    iodo: Annotated[
        Optional[bool],
        typer.Option('--iodo/--no-iodo', help='Add (--iodo) or remove (--no-iodo) carbamidomethylation of cysteine as a static modification'),
    ] = None,
    ox: Annotated[
        Optional[bool],
        typer.Option('--ox/--no-ox', help='Add (--ox) or remove (--no-ox) oxidation of methionine as a variable modification'),
    ] = None,
    phos: Annotated[
        Optional[bool],
        typer.Option('--phos/--no-phos', help='Add (--phos) or remove (--no-phos) phosphorylation of serine/threonine/tyrosine as a variable modification'),
    ] = None,
    n_cyc: Annotated[
        Optional[bool],
        typer.Option('--n-cyc/--no-n-cyc', help='Add (--n-cyc) or remove (--no-n-cyc) cyclisation of peptide N-terminal glutamine to pyro-glutamic acid as a variable modification'),
    ] = None,
    n_ace: Annotated[
        Optional[bool],
        typer.Option('--n-ace/--no-n-ace', help='Add (--n-ace) or remove (--no-n-nace) acetylation of protein N-terminal residue as a variable modification'),
    ] = None,
    custom: Annotated[
        Optional[str],
        typer.Option('--custom', help='Add a custom variable modification following Tide mods_spec format; can be passed multiple times; pass empty string "" to remove all custom modifications')
    ] = None,
    clip_met: Annotated[
        Optional[bool],
        typer.Option('--clip-met/--no-clip-met', help="Include (--clip-met) or don't include (--no-clip-met) duplicate N-terminal peptides with clipped N-terminal methionine")
    ] = None,
    low_res: Annotated[
        Optional[bool],
        typer.Option('--low-res/--high-res', help='Set search parameters for low-resolution (--low-res) or high-resolution (--high-res) instruments'),
    ] = None,
    organism: Annotated[
        Optional[List[str]],
        typer.Option('--organism', help='Set organism header patterns for per-organism picked protein FDR [/dim](format: OrganismLabel=Pattern)[/dim]'),
    ] = None,
    mbr: Annotated[
        Optional[bool],
        typer.Option('--mbr/--no-mbr', help='Use match between runs option when running LFQ command'),
    ] = None
):
    '''
    Set values in user configuration file
    '''
    configFuncs.config_set(
        iodo=iodo,
        ox=ox,
        phos=phos,
        n_cyc=n_cyc,
        n_ace=n_ace,
        custom=custom,
        clip_met=clip_met,
        low_res=low_res,
        organism=organism,
        mbr=mbr,
    )