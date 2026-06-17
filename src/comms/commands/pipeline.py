'''
comMS pipeline functions
'''
# -- Import external dependencies
import datetime
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.samples import loadSampleSheet
from comms.utils.context import ExperimentContext
from comms.commands import convert, index, search, rescore, lfq, quantify, report

# -- run_pipeline: runs the full comMS pipeline end-to-end from a sample sheet
def run_pipeline(
    sample_sheet: Path,
    database: Path,
    input_dir: Path,
    ctx: ExperimentContext,
    param_medic: bool,
    skip_convert: bool,
    skip_lfq: bool,
    skip_quantify: bool,
    skip_report: bool,
    threads: int | None,
    org_tags: str
):
    logMsg('pipeline')
    logMsg.debug(f'Started command: pipeline')
    threads = threads or ctx.config['search']['threads']
    START = datetime.datetime.now()
    # -- Load sample sheet
    try:
        samples = loadSampleSheet(sample_sheet)
    except ValueError as e:
        logMsg.error(f'Could not load sample sheet: {e}')
        raise SystemExit(1)
    logMsg.debug(f"Sample sheet loaded: {len(samples)} sample(s); {samples['treatment'].nunique()} treatment(s)")
    logMsg.info(f'Running comMS pipeline: {len(samples)} sample(s), {samples['treatment'].nunique()} treatment(s)')
    # -- Step 1: Convert (optional)
    if not skip_convert:
        logMsg.progress(f'Step 1/5: converting .RAW files')
        convert.run_convert(input_dir=input_dir, ctx=ctx, gzip=True, in_pipeline=True)
        mzml_dir = ctx.root / 'comms/results/convert'
    else:
        logMsg.progress(f'Step 1/5: skipping .RAW conversion')
        mzml_dir = input_dir
    logMsg.debug(f'mzml_dir: {mzml_dir}')
    # -- Step 2: Build index
    logMsg.progress(f'Step 2/5: building peptide index')
    index.run_index(database=database, ctx=ctx, in_pipeline=True)
    index_dir = ctx.root / 'comms/results/index'
    logMsg.debug(f'index_dir: {index_dir}')
    # -- Step 3: Search
    logMsg.progress(f'Step 3/5: searching spectra')
    search.run_search(
        input_dir=mzml_dir,
        index_dir=index_dir,
        ctx=ctx,
        param_medic=param_medic,
        threads=threads,
        in_pipeline=True
    )
    search_dir = ctx.root / 'comms/results/search'
    logMsg.debug(f'search_dir: {search_dir}')
    # -- Step 4: Rescore
    logMsg.progress(f'Step 4/5: rescoring PSMs')
    rescore.run_rescore(input_dir=search_dir, database=database, ctx=ctx, organism_tags=org_tags, in_pipeline=True)
    rescore_dir = ctx.root / 'comms/results/rescore'
    logMsg.debug(f'rescore_dir: {rescore_dir}')
    # -- Step 5: Quantify
    if skip_lfq and skip_quantify:
        logMsg.progress(f'Step 5/5: quantification skipped')
    else:
        logMsg.progress(f'Step 5/5: quantifying peptides/proteins')
        num_steps = int(not skip_lfq) + int(not skip_quantify)
        step = 1
        if not skip_lfq:
            # -- Step 5a: MS1 label free quantification
            logMsg.progress(f'\tStep {step}/{num_steps}: quantifying with MS1 label-free quantification')
            lfq.run_lfq(rescore_dir=rescore_dir, mzml_dir=mzml_dir, sample_sheet=sample_sheet, ctx=ctx, in_pipeline=True)
            lfq_dir = ctx.root / 'comms/results/lfq'
            logMsg.debug(f'lfq_dir: {lfq_dir}')
        if not skip_quantify:
            # -- Step 5b: dNSAF spectral counting
            logMsg.progress(f'\tStep {step}/{num_steps}: quantifying with dNSAF spectral counting...')
            quantify.run_quantify(input_dir=rescore_dir, database=database, ctx=ctx, in_pipeline=True)
            quantify_dir = ctx.root / 'comms/results/quantify'
            logMsg.debug(f'quantify_dir: {quantify_dir}')
    END = datetime.datetime.now()
    logMsg.info(f'Pipeline complete, runtime {END - START}, results written to {ctx.root}')
    logMsg.debug(f'Finished command: pipeline')