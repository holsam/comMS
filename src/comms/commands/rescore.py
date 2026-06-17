'''
comMS rescore functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from typing import Optional

# -- Import internal functions
from comms.utils.fasta import splitFastaByOrganism
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.settings import ExperimentContext
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_rescore: rescores all Tide-search PSM files using Percolator on the full combined database, then splits output by organism and runs assign-confidence per organism for per-organism q-values
def run_rescore(input_dir: Path, database: Path, ctx: ExperimentContext, organism_tags: Optional[str] = None, in_pipeline: bool = False):
    if not in_pipeline:
        logMsg('rescore')
    logMsg.debug('Started command: rescore')
    crux_bin, _ = validate(check_crux=True, bin_dir=ctx.bin_dir)
    logMsg.debug(f'Scanning {input_dir }for Tide-search PSMs')
    target_files = sorted(input_dir.glob('[!.]*.tide-search.target.txt'))
    if not target_files:
        logMsg.error(f'No Tide-search target PSM files found in {input_dir}')
        raise SystemExit(1)
    logMsg.info(f'Rescoring {len(target_files)} PSM file(s)')
    # Parse organism tags
    logMsg.debug('Resolving organism tags')
    if organism_tags:
        organism_tags = _parseOrganismTags(organism_tags)
    else:
        if ctx.config['organism']:
            organism_tags = ctx.config['organism']
        else:
            logMsg.error(f'No organism tags supplied and none found in config')
            raise SystemExit(1)
    logMsg.debug(f'Organism tags: {organism_tags}')
    # Generate output file structure
    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'rescore')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'rescore.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    # Build per-organism sub-FASTAs (used by assign-confidence in round 2)
    sub_fastas = splitFastaByOrganism(database, out_dir, organism_tags)
    logMsg.debug(f'Built {len(sub_fastas)} per-organism sub-FASTA(s)')
    # Round 1: Percolator on the full combined database, with one call per sample file
    logMsg.progress(f'Round 1: Rescoring {len(target_files)} file(s) using full combined database')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for target_file in tqdm(target_files, desc='Files rescored'):
            logMsg.progress(f'Round 1: rescoring {target_file.name}')
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
                logMsg.debug(f'Round 1: rescored {target_file.name} saved to {out_dir / fileroot}.percolator.target.psms.txt')
            else:
                logMsg.warn(f'Round 1: rescoring failed for {target_file.name}')
                n_fail += 1
    logMsg.info(f'Round 1 complete: {n_ok} succeeded, {n_fail} failed')
    # Collect the combined Percolator outputs for splitting
    combined_target_files = sorted(out_dir.glob('[!.]*.percolator.target.psms.txt'))
    if not combined_target_files:
        logMsg.error('Round 2: no combined Percolator output files found after round 1, cannot continue')
        raise SystemExit(1)
    
    # Round 2: split Percolator output by organism prefix, then run assign-confidence per organism for per-organism PSM-level q-values
    logMsg.progress(f'Round 2: splitting and assigning confidence to {len(combined_target_files)} file(s)')
    ac_n_ok, ac_n_fail = 0, 0
    with logging_redirect_tqdm():
        for combined_file in tqdm(combined_target_files, desc='Files processed'):
            logMsg.progress(f'Round 2: processing {combined_file.name}')
            fileroot = combined_file.name.removesuffix('.percolator.target.psms.txt')
            combined_decoy_file = out_dir / f'{fileroot}.percolator.decoy.psms.txt'
            # Split target and decoy files by organism
            split_ok = _splitPsmsByOrganism(
                target_file=combined_file,
                decoy_file=combined_decoy_file,
                organism_tags=organism_tags,
                out_dir=out_dir,
                fileroot=fileroot,
            )
            if not split_ok:
                logMsg.warn(f'Round 2: {combined_file.name} PSMs could not be split')
                ac_n_fail += len(sub_fastas)
                continue
            # Run assign-confidence on each organism's split target file
            for label in sub_fastas.keys():
                org_out_dir = out_dir / label
                org_target = org_out_dir / f'{fileroot}.{label}.percolator.target.psms.txt'
                if not org_target.exists():
                    logMsg.warn(f'Round 2: split target missing for {label}: {org_target.name}')
                    ac_n_fail += 1
                    continue
                ac_fileroot = f'{fileroot}.{label}'
                ok = cruxutil.assignConfidence(
                    crux_bin=crux_bin,
                    target_psm_file=org_target,
                    out_dir=org_out_dir,
                    fileroot=ac_fileroot,
                )
                if ok:
                    ac_n_ok += 1
                    logMsg.debug(
                        f'Round 2: processed {combined_file.name} saved to {org_out_dir / ac_fileroot}.assign-confidence.target.txt'
                    )
                else:
                    logMsg.warn(f'Round 2: processing failed for {label}: {org_target.name}')
                    ac_n_fail += 1
    logMsg.info(f'Round 2 complete: {ac_n_ok} succeeded, {ac_n_fail} failed')
    logMsg.debug(f'Finished command: rescore')

# -- _splitPsmsByOrganism: returns True on success, False on any file error
def _splitPsmsByOrganism(
    target_file: Path,
    decoy_file: Path,
    organism_tags: dict[str, str],
    out_dir: Path,
    fileroot: str,
) -> bool:
    try:
        for psm_type, psm_file in [('target', target_file), ('decoy', decoy_file)]:
            if not psm_file.exists():
                logMsg.warn(f'Round 2: PSM file not found, skipping split: {psm_file.name}')
                continue
            with psm_file.open('r') as f:
                header = f.readline()
                rows = f.readlines()
            # Get indice for proteinIds column in header
            id_index = _findProteinIdsIndex(header)
            # Partition rows by organism tag
            buckets: dict[str, list[str]] = {}
            for row in rows:
                label = _classifyPsmRow(row, id_index, organism_tags)
                buckets.setdefault(label, []).append(row)
            # Write each bucket
            for label, label_rows in buckets.items():
                label_dir = out_dir / label
                label_dir.mkdir(parents=True, exist_ok=True)
                out_file = label_dir / f'{fileroot}.{label}.percolator.{psm_type}.psms.txt'
                with out_file.open('w') as f:
                    f.write(header)
                    f.writelines(label_rows)
                logMsg.debug(f'Wrote {len(label_rows)} {psm_type} PSMs: {out_file.name}')
        return True
    except Exception as e:
        logMsg.debug(f'Exception splitting {fileroot}: {e}')
        return False

# -- _findProteinIdsIndex: returns the column indice for the proteinIds column from a PSM file header
def _findProteinIdsIndex(header: str):
    header = header.rstrip('\n').split('\t')
    return [i for i, x in enumerate(header) if x == 'proteinIds'][0]

# -- _classifyPsmRow: returns the organism label for a single PSM row based on the protein ID column
def _classifyPsmRow(row: str, id_index: int, organism_tags: dict[str, str]) -> str:
    parts = row.rstrip('\n').split('\t')
    if not parts or parts == ['']:
        return 'contaminants'
    protein_id = parts[id_index]
    for label, tag in organism_tags.items():
        if tag in protein_id:
            return label
    return 'contaminants'

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