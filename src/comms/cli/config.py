'''
comMS CLI subcommand for managing configuration files
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, List, Literal, Optional

# -- Import internal functions
from comms.commands import config as configFuncs

# -- Initialise config Typer class
commsConfig = typer.Typer(add_completion=False, invoke_without_command=True)

# -- Define shared path/global parameters
_PATH_ARG = typer.Argument(help='Path to experiment directory [dim](default: ".")[/dim]')
_GLOBAL_OPT = typer.Option('--global', help='Use the global user config instead of a local config.toml')

# -- Define config command (single command, no subcommands)
@commsConfig.command(rich_help_panel='comMS Configuration')
def config(
    # -- Global options --
    path: Annotated[Optional[Path], _PATH_ARG] = None,
    global_: Annotated[bool, _GLOBAL_OPT] = False,
    verify: Annotated[bool, typer.Option('--verify', help='Check that all expected keys are present')] = False,
    reset: Annotated[bool, typer.Option('--reset', help='Overwrite with comMS built-in defaults')] = False,
    force: Annotated[bool, typer.Option('--force', help='Skip confirmation when using --reset')] = False,
    # -- convert command options --
    gzip: Annotated[Optional[bool], typer.Option('--gzip/--no-gzip', help='Compress mzML output using gzip')] = None,
    format: Annotated[Optional[int], typer.Option('--format', help='ThermoRawFileParser output format code', min=0, max=4)] = None,
    metadata: Annotated[Optional[int], typer.Option('--metadata', help='ThermoRawFileParser metadata capture code', min=0, max=2)] = None,
    # -- index command options --
    iodo: Annotated[Optional[bool], typer.Option('--iodo/--no-iodo', help='Add or remove carbamidomethylation of cysteine as a static modification')] = None,
    ox: Annotated[Optional[bool], typer.Option('--ox/--no-ox', help='Add or remove oxidation of methionine as a variable modification')] = None,
    phos: Annotated[Optional[bool], typer.Option('--phos/--no-phos', help='Add or remove phosphorylation of serine/threonine/tyrosine as a variable modification')] = None,
    n_cyc: Annotated[Optional[bool], typer.Option('--n-cyc/--no-n-cyc', help='Add or remove cyclisation of peptide N-terminal glutamine to pyro-glutamic acid')] = None,
    n_ace: Annotated[Optional[bool], typer.Option('--n-ace/--no-n-ace', help='Add or remove acetylation of protein N-terminal residue')] = None,
    custom: Annotated[Optional[str], typer.Option('--custom', help='Add a custom variable modification (Tide mods_spec format); use "" to clear all custom mods')] = None,
    clip_met: Annotated[Optional[bool], typer.Option('--clip-met/--no-clip-met', help='Include or exclude duplicate N-terminal peptides with clipped N-terminal methionine')] = None,
    missed_cleavages: Annotated[Optional[int], typer.Option('--missed-cleavages', help='Number of missed enzymatic cleavages allowed', min=0)] = None,
    organism: Annotated[Optional[List[str]], typer.Option('--organism', help='Organism header pattern for per-organism picked protein FDR [dim](format: Label=Pattern)[/dim]')] = None,
    low_res: Annotated[Optional[bool], typer.Option('--low-res/--high-res', help='Set score_function/mz_bin_width for low- or high-resolution instruments')] = None,
    # -- search command options --
    score_function: Annotated[Optional[str], typer.Option('--score-function', help='Tide-search score function')] = None,
    min_peaks: Annotated[Optional[int], typer.Option('--min-peaks', help='Minimum peaks required per spectrum', min=1)] = None,
    precursor_tolerance_ppm: Annotated[Optional[float], typer.Option('--precursor-tolerance-ppm', help='Precursor mass tolerance in ppm')] = None,
    mz_bin_width: Annotated[Optional[float], typer.Option('--mz-bin-width', help='Fragment m/z bin width in Da')] = None,
    threads: Annotated[Optional[int], typer.Option('--threads', help='Default number of threads', min=1)] = None,
    # -- percolator command options --
    protein_enzyme: Annotated[Optional[str], typer.Option('--protein-enzyme', help='Enzyme used for protein-level picked-FDR grouping')] = None,
    picked_protein: Annotated[Optional[bool], typer.Option('--picked-protein/--no-picked-protein', help='Use picked-protein FDR')] = None,
    shared_psm: Annotated[Optional[Literal['drop', 'include']], typer.Option('--shared-psm', help='Policy for PSMs shared between organisms')] = None,
    # -- quantify command options --
    measure: Annotated[Optional[Literal['NSAF', 'dNSAF', 'SIN', 'EMPAI']], typer.Option('--measure', help='Spectral-counting measure')] = None,
    qvalue_threshold: Annotated[Optional[float], typer.Option('--qvalue-threshold', help='PSM q-value threshold for quantification', min=0.0, max=1.0)] = None,
    unique_mapping: Annotated[Optional[bool], typer.Option('--unique-mapping/--no-unique-mapping', help='Require unique peptide-to-protein mapping')] = None,
    # -- report command options --
    min_reps: Annotated[Optional[int], typer.Option('--min-reps', help='Minimum replicates per fraction-treatment group', min=1)] = None,
    lfc_threshold: Annotated[Optional[float], typer.Option('--lfc-threshold', help='|log2FC| threshold for DA', min=0.0)] = None,
    fdr_threshold: Annotated[Optional[float], typer.Option('--fdr-threshold', help='BH-FDR threshold for DA', min=0.0, max=1.0)] = None,
    top_n: Annotated[Optional[int], typer.Option('--top-n', help='Number of top DA proteins labelled per volcano plot', min=1)] = None,
) -> None:
    '''
    View or edit comMS configurations
    '''
    if reset:
        configFuncs.config_reset(path, global_, force=force)
        return
    if verify:
        configFuncs.config_verify(path, global_)
        return
    changed = configFuncs.config_set(
        path,
        global_,
        gzip=gzip,
        format=format,
        metadata=metadata,
        iodo=iodo,
        ox=ox,
        phos=phos,
        n_cyc=n_cyc,
        n_ace=n_ace,
        custom=custom,
        clip_met=clip_met,
        missed_cleavages=missed_cleavages,
        organism=organism,
        low_res=low_res,
        score_function=score_function,
        min_peaks=min_peaks,
        precursor_tolerance_ppm=precursor_tolerance_ppm,
        mz_bin_width=mz_bin_width,
        threads=threads,
        protein_enzyme=protein_enzyme,
        picked_protein=picked_protein,
        shared_psm=shared_psm,
        measure=measure,
        qvalue_threshold=qvalue_threshold,
        unique_mapping=unique_mapping,
        min_reps=min_reps,
        lfc_threshold=lfc_threshold,
        fdr_threshold=fdr_threshold,
        top_n=top_n,
    )
    if not changed:
        configFuncs.config_list(path, global_)