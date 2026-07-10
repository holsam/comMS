'''
comMS CLI subcommand for indexing proteomes
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import index as indexFuncs
from comms.utils.context import ExperimentContext

# -- Initialise index Typer class
commsIndex = typer.Typer(add_completion=False)

# -- index: builds a peptide index from a pre-merged combined FASTA database using peptide-level reverse decoys and modifications defined in config.toml
@commsIndex.command(help='Generate a peptide index from a FASTA file', rich_help_panel='Protein Identification')
def index(
    database: Annotated[
        Optional[Path],
        typer.Option('-f', '--fasta', help='Path to FASTA file [dim][default: experiment database file][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    iodo: Annotated[Optional[bool], typer.Option('--iodo/--no-iodo', help='Override carbamidomethylation of cysteine for this run only [dim][default: config][/dim]')] = None,
    ox: Annotated[Optional[bool], typer.Option('--ox/--no-ox', help='Override oxidation of methionine for this run only [dim][default: config][/dim]')] = None,
    phos: Annotated[Optional[bool], typer.Option('--phos/--no-phos', help='Override phosphorylation of S/T/Y for this run only [dim][default: config][/dim]')] = None,
    n_cyc: Annotated[Optional[bool], typer.Option('--n-cyc/--no-n-cyc', help='Override N-terminal Gln cyclisation for this run only [dim][default: config][/dim]')] = None,
    n_ace: Annotated[Optional[bool], typer.Option('--n-ace/--no-n-ace', help='Override N-terminal protein acetylation for this run only [dim][default: config][/dim]')] = None,
    custom: Annotated[Optional[str], typer.Option('--custom', help='Add a custom variable modification for this run only [dim][default: config][/dim]')] = None,
    clip_met: Annotated[Optional[bool], typer.Option('--clip-met/--no-clip-met', help='Override clipped N-terminal methionine handling for this run only [dim][default: config][/dim]')] = None,
    missed_cleavages: Annotated[Optional[int], typer.Option('--missed-cleavages', help='Missed cleavages for this run only [dim][default: config index.missed_cleavages][/dim]', min=0)] = None,
):
    ctx = ExperimentContext.resolve(experiment_dir)
    indexFuncs.run_index(
        database,
        ctx,
        iodo=iodo,
        ox=ox,
        phos=phos,
        n_cyc=n_cyc,
        n_ace=n_ace,
        custom=custom,
        clip_met=clip_met,
        missed_cleavages=missed_cleavages,
    )