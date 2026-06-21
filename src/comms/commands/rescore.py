'''
src/comms/commands/rescore.py
'''

# -- Import external dependencies
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Dict, Optional
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.fasta import splitFastaByOrganism
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.context import ExperimentContext, resolve_database, resolve_results_input
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_rescore: rescores all Tide-search PSM files using Percolator on the full combined database, then:
# - single-species: run assign-confidence
# - multi-species: split output by organism and run assign-confidence per organism for per-organism q-values
def run_rescore(
    input_dir,
    database,
    ctx: ExperimentContext,
    organism_tags: Optional[str] = None,
    in_pipeline: bool = False,
):
    if not in_pipeline:
        logMsg('rescore')
    logMsg.debug('Started command: rescore')
    crux_bin, _ = validate(check_crux=True, bin_dir=ctx.bin_dir)
    input_dir = resolve_results_input(ctx, 'search', input_dir)
    database = resolve_database(ctx, database)
    target_files = sorted(input_dir.glob('[!.]*.tide-search.target.txt'))
    if not target_files:
        logMsg.error(f'No Tide-search target PSM files found in {input_dir}')
        raise SystemExit(1)
    logMsg.info(f'Rescoring {len(target_files)} PSM file(s)')
    # Resolve analysis mode
    mode = ctx.analysis_mode
    if mode is None:
        mode = 'multi' if (organism_tags or ctx.config.get('organism')) else 'single'
    multispecies = mode != 'single'
    if not multispecies and organism_tags:
        logMsg.warn('Single-species analysis: ignoring supplied organism tags')

    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'rescore')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'rescore.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    # Round 1: run Percolator on the full combined database, with one call per sample file
    combined_target_files = _run_combined_percolator_round(
        crux_bin, target_files, database, out_dir, ctx,
    )
    if not combined_target_files:
        logMsg.error('No combined Percolator output found, cannot continue')
        raise SystemExit(1)
    # Round 2: run Percolator on each organism sub-FASTA if multispecies analysis
    if multispecies:
        organism_tags = (
            _parseOrganismTags(organism_tags)
            if organism_tags
            else ctx.config.get('organism')
        )
        if not organism_tags:
            logMsg.error('No organism tags supplied or configured for multi-species analysis')
            raise SystemExit(1)
        logMsg.debug(f'Organism tags: {organism_tags}')
        sub_fastas = splitFastaByOrganism(database, out_dir, organism_tags)
        logMsg.debug(f'Built {len(sub_fastas)} per-organism sub-FASTA(s)')
        _run_per_organism_percolator_round(
            crux_bin, target_files, sub_fastas, organism_tags, out_dir, ctx
        )
    # Log command as complete
    logMsg.debug('Finished command: rescore')

# -- _run_percolator_round: returns list of PSM files after runn Percolator (via Crux) on database, with one call per sample file
def _run_combined_percolator_round(crux_bin, target_files, database, out_dir, ctx) -> list:
    logMsg.progress(f'Rescoring {len(target_files)} file(s) using combined database')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for target_file in tqdm(target_files, desc='Files rescored'):
            logMsg.progress(f'Rescoring {target_file.name}')
            fileroot = target_file.name.removesuffix('.tide-search.target.txt')
            ok = cruxutil.percolator(
                crux_bin=crux_bin,
                target_psm_file=target_file,
                database=database,
                out_dir=out_dir,
                fileroot=fileroot,
                config=ctx.config,
            )
            if ok:
                n_ok += 1
                logMsg.debug(f'Rescored {target_file.name} saved to {out_dir / fileroot}.percolator.target.psms.txt')
            else:
                n_fail += 1
                logMsg.warn(f'Rescoring failed for {target_file.name}')
    logMsg.info(f'Combined rescoring complete: {n_ok} succeeded, {n_fail} failed')
    return sorted(out_dir.glob('[!.]*.percolator.target.psms.txt'))

# -- _run_per_organism_percolator_round: returns None but splits combined Tide search outputs by organism and runs Percolator (via Crux)
def _run_per_organism_percolator_round(crux_bin, combined_target_files, sub_fastas, organism_tags, out_dir, ctx):
    logMsg.progress(f'Rescoring {len(combined_target_files)} file(s) using per-organism sub-FASTAs')
    n_ok, n_fail = 0, 0
    shared_policy = ctx.config['percolator']['shared_psm']
    with logging_redirect_tqdm():
        for combined_file in tqdm(combined_target_files, desc='Files rescored'):
            logMsg.progress(f'Rescoring {combined_file.name}')
            fileroot = combined_file.name.removesuffix('.tide-search.target.txt')
            combined_decoy_file = combined_file.parent / f'{fileroot}.tide-search.decoy.txt'
            # Split target and decoy files by organism
            split_ok = _splitPsmsByOrganism(
                target_file=combined_file,
                decoy_file=combined_decoy_file,
                organism_tags=organism_tags,
                out_dir=out_dir,
                fileroot=fileroot,
                shared_policy = shared_policy,
            )
            if not split_ok:
                logMsg.warn(f'{combined_file.name} PSMs could not be split by organism')
                n_fail += len(sub_fastas)
                continue
            # Run percolator on each organism's split target file
            for label in sub_fastas.keys():
                org_out_dir = out_dir / label
                org_target = org_out_dir / f'{fileroot}.{label}.tide-search.target.txt'
                if not org_target.exists():
                    logMsg.warn(f'Split target missing for {label}: {org_target.name}')
                    n_fail += 1
                    continue
                org_fileroot = f'{fileroot}.{label}'
                ok = cruxutil.percolator(
                    crux_bin=crux_bin,
                    target_psm_file=org_target,
                    database=sub_fastas[label],
                    out_dir=org_out_dir,
                    fileroot=org_fileroot,
                    config=ctx.config,
                )
                if ok:
                    n_ok += 1
                    logMsg.debug(f'Rescored {combined_file.name} saved to {org_out_dir / org_fileroot}.percolator.target.psms.txt')
                else:
                    n_fail += 1
                    logMsg.warn(f'Round 2: processing failed for {label}: {org_target.name}')
    logMsg.info(f'Round 2 complete: {n_ok} succeeded, {n_fail} failed')

# -- _splitPsmsByOrganism: returns True on success, False on any file error
def _splitPsmsByOrganism(
    target_file: Path,
    decoy_file: Path,
    organism_tags: dict[str, str],
    out_dir: Path,
    fileroot: str,
    shared_policy: str,
) -> bool:
    try:
        for psm_type, psm_file in [('target', target_file), ('decoy', decoy_file)]:
            if not psm_file.exists():
                logMsg.warn(f'PSM file {psm_file.name} not found, skipping split')
                continue
            with psm_file.open('r') as f:
                header = f.readline()
                rows = f.readlines()
            # Get indice for protein id column in header
            id_index = _findProteinIdsIndex(header, 'protein id')
            # Partition rows by organism tag
            shared_count = 0
            dropped_rows = []
            buckets: dict[str, list[str]] = {}
            for row in rows:
                # Get organism labels for row
                label = _classifyPsmRow(row, id_index, organism_tags)
                # If in more than one organism:
                if len(label) > 1:
                    if shared_policy == 'drop':
                        shared_count += 1
                        dropped_rows.append(row)
                    elif shared_policy == 'include':
                        shared_count += 1
                        for l in label:
                            buckets.setdefault(l, []).append(row)
                    else:
                        logMsg.warn(f'Unknown shared PSM policy {shared_policy}, falling back to "drop"')
                        shared_count += 1
                        dropped_rows.append(row)
                else:
                    buckets.setdefault(label[0], []).append(row)
            # If shared_count > 0, print an info message
            logMsg.info(f'{psm_type}: {shared_count} shared-organism PSMs detected, handled with shared PSM policy {shared_policy}')
            # Write each bucket
            for label, label_rows in buckets.items():
                label_dir = out_dir / label
                label_dir.mkdir(parents=True, exist_ok=True)
                out_file = label_dir / f'{fileroot}.{label}.tide-search.{psm_type}.txt'
                with out_file.open('w') as f:
                    f.write(header)
                    f.writelines(label_rows)
                logMsg.debug(f'Wrote {len(label_rows)} {psm_type} PSMs: {out_file.name}')
        return True
    except Exception as e:
        logMsg.debug(f'Exception splitting {fileroot}: {e}')
        return False

# -- _findProteinIdsIndex: returns the column indice for the proteinIds column from a PSM file header
def _findProteinIdsIndex(header: str, col_name: str):
    header = header.rstrip('\n').split('\t')
    return [i for i, x in enumerate(header) if x == col_name][0]

# -- _classifyPsmRow: returns the organism label for a single PSM row based on the protein ID column
def _classifyPsmRow(row: str, id_index: int, organism_tags: dict[str, str]) -> list[str]:
    parts = row.rstrip('\n').split('\t')
    if not parts or parts == ['']:
        return ['contaminants']
    label_matches = []
    protein_id = parts[id_index]
    for label, tag in organism_tags.items():
        if tag in protein_id:
            label_matches.append(label)
    return label_matches if label_matches else ['contaminants']

# -- _parseOrganismTags: returns dictionary of strings corresponding to organism tags from comma-separated input
def _parseOrganismTags(input_string: str):
    input_string = ''.join(input_string.split())    # strip whitespace
    items = input_string.split(',')    # split by comma
    # Check even number of items (i.e. no organism without patterns etc)
    if len(items) % 2:
        logMsg.error(f'Invalid organism tags: {input_string}')
        raise SystemExit(1)
    tags = {}
    for i in range(len(items)):
        if i % 2:
            tags.update({items[i-1]: items[i]})
    return tags