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
from comms.utils.context import ExperimentContext, resolve_database, resolve_data_files, resolve_sample_sheet
from comms.commands import convert, index, search, rescore, lfq, quantify, report

# -- run_pipeline: runs the full comMS pipeline end-to-end from a sample sheet
def run_pipeline(
        sample_sheet,
        database,
        data,
        ctx: ExperimentContext,
        param_medic,
        skip_convert,
        skip_lfq,
        skip_quantify,
        skip_report,
        threads,
        org_tags
):
    logMsg('pipeline')
    logMsg.debug(f'Started command: pipeline')

    # Resolve external inputs once
    data_files = resolve_data_files(ctx, data)
    database = resolve_database(ctx, database)
    sample_sheet = resolve_sample_sheet(ctx, sample_sheet)
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
        convert.run_convert(data_files, ctx=ctx, gzip=True, in_pipeline=True)
        mzml_override = None # search/lfq glob the convert results
    else:
        logMsg.progress(f'Step 1/5: skipping .RAW conversion')
        mzml_override = [f for f in data_files if f.suffix.lower() == '.mzml' or f.name.endswith('.mzML.gz')]
    # -- Step 2: Build index
    logMsg.progress(f'Step 2/5: building peptide index')
    index.run_index(database=database, ctx=ctx, in_pipeline=True)
    # -- Step 3: Search
    logMsg.progress(f'Step 3/5: searching spectra')
    search.run_search(
        mzml_override,
        index_dir=None,
        ctx=ctx,
        param_medic=param_medic,
        threads=threads,
        in_pipeline=True
    )
    # -- Step 4: Rescore
    logMsg.progress(f'Step 4/5: rescoring PSMs')
    rescore.run_rescore(
        input_dir=None,
        database=database,
        ctx=ctx,
        organism_tags=org_tags,
        in_pipeline=True
)
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
            lfq.run_lfq(rescore_dir=None, data_files=mzml_override, sample_sheet=sample_sheet, ctx=ctx, in_pipeline=True)
            step += 1
        if not skip_quantify:
            # -- Step 5b: dNSAF spectral counting
            logMsg.progress(f'\tStep {step}/{num_steps}: quantifying with dNSAF spectral counting')
            quantify.run_quantify(input_dir=None, database=database, ctx=ctx, in_pipeline=True)

    END = datetime.datetime.now()
    logMsg.info(f'Pipeline complete, runtime {END - START}, results written to {ctx.root}')
    logMsg.debug(f'Finished command: pipeline')