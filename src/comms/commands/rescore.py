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
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_rescore: rescores all Tide-search PSM files using Percolator on the full combined database, then splits output by organism and runs assign-confidence per organism for per-organism q-values
def run_rescore(input_dir: Path, database: Path, output: Path, org_tags: Optional[str], in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('rescore')
        log.debug('Starting rescore command')
    
    crux_bin, _ = validate(check_crux=True)
    
    logMsg.debug(f'Scanning for Tide-search PSM files in: {input_dir}')
    target_files = sorted(input_dir.glob('[!.]*.tide-search.target.txt'))
    if not target_files:
        logMsg.error(f'No Tide-search target PSM files found in: {input_dir}')
        print(f'[bold red]ERROR:[/bold red] No Tide-search target PSM files found in {input_dir}.')
        raise SystemExit(1)
    logMsg.info(f'Found {len(target_files)} PSM file(s)')
    
    logMsg.debug('Parsing organism tags')
    if org_tags:
        organism_tags = _parseOrganismTags(org_tags)
    else:
        if config['organism']:
            organism_tags = config['organism']
        else:
            logMsg.error(f'No organism tag data found in user config file.')
            print(f'[bold red]ERROR:[/bold red] No organism tag data found in user config file. Set for one command only using [bold]--organism-tags[/] or set in user config using [bold]comms config set --organism[/bold].')
            raise SystemExit(1)
    
    out_dir = pathutil.generateOutputFileStructure(output, 'rescore')
    log_path = out_dir / 'rescore.log'
    # Build per-organism sub-FASTAs (used by assign-confidence in round 2)
    sub_fastas = splitFastaByOrganism(database, out_dir, organism_tags)

    # Round 1: Percolator on the full combined database, with one call per sample file
    print(f'\nRound 1: Rescoring {len(target_files)} PSM file(s) with Percolator (full combined database)...')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for target_file in tqdm(target_files, desc='Files rescored'):
            fileroot = target_file.name.removesuffix('.tide-search.target.txt')
            ok = cruxutil.percolator(
                crux_bin=crux_bin,
                target_psm_file=target_file,
                database=database,
                out_dir=out_dir,
                fileroot=fileroot,
                config=config,
            )
            if ok:
                n_ok += 1
                logMsg.debug(f'Percolator output written to: {out_dir / fileroot}.percolator.target.psms.txt')
            else:
                logMsg.warn(f'Percolator failed for: {target_file.name}')
                n_fail += 1
    logMsg.info(f'Round 1 complete — {n_ok} succeeded, {n_fail} failed')
    if n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] Percolator failed for {n_fail} file(s). Check {log_path} for details.')
    # Collect the combined Percolator outputs for splitting
    combined_target_files = sorted(out_dir.glob('[!.]*.percolator.target.psms.txt'))
    if not combined_target_files:
        logMsg.error('No combined Percolator output files found after round 1 — cannot proceed.')
        print(f'[bold red]ERROR:[/bold red] No Percolator output found in {out_dir}.')
        raise SystemExit(1)
    
    # Round 2: split Percolator output by organism prefix, then run assign-confidence per organism for per-organism PSM-level q-values
    print(f'\nRound 2: Splitting and running assign-confidence on {len(combined_target_files)} file(s)...')
    ac_n_ok, ac_n_fail = 0, 0
    with logging_redirect_tqdm():
        for combined_file in tqdm(combined_target_files, desc='Files processed'):
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
                logMsg.warn(f'Could not split PSMs for: {combined_file.name}')
                ac_n_fail += len(sub_fastas)
                continue
            # Run assign-confidence on each organism's split target file
            for label in sub_fastas.keys():
                org_out_dir = out_dir / label
                org_target = org_out_dir / f'{fileroot}.{label}.percolator.target.psms.txt'
                if not org_target.exists():
                    logMsg.warn(f'Split target file not found for {label}: {org_target.name}')
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
                        f'assign-confidence output: '
                        f'{org_out_dir / ac_fileroot}.assign-confidence.target.txt'
                    )
                else:
                    logMsg.warn(f'assign-confidence failed for {label}: {org_target.name}')
                    ac_n_fail += 1
    logMsg.info(f'Round 2 complete — {ac_n_ok} succeeded, {ac_n_fail} failed')
    if ac_n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] assign-confidence failed for {ac_n_fail} file(s). Check {log_path} for details.')
    print(f'\n[bold green]Rescore finished successfully — summary:[/]')
    print(f'- Round 1 (Percolator): {n_ok} succeeded, {n_fail} failed')
    print(f'- Round 2 (assign-confidence): {ac_n_ok} succeeded, {ac_n_fail} failed')
    print(f'- Output directory: {out_dir}\n')

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
                logMsg.warn(f'PSM file not found, skipping split: {psm_file.name}')
                continue
            with psm_file.open('r') as f:
                header = f.readline()
                rows = f.readlines()
            # Partition rows by organism tag
            buckets: dict[str, list[str]] = {}
            for row in rows:
                label = _classifyPsmRow(row, organism_tags)
                buckets.setdefault(label, []).append(row)
            # Write each bucket
            for label, label_rows in buckets.items():
                label_dir = out_dir / label
                label_dir.mkdir(parents=True, exist_ok=True)
                out_file = label_dir / f'{fileroot}.{label}.percolator.{psm_type}.psms.txt'
                with out_file.open('w') as f:
                    f.write(header)
                    f.writelines(label_rows)
                logMsg.debug(f'Wrote {len(label_rows)} {psm_type} PSMs to: {out_file.name}')
        return True
    except Exception as e:
        logMsg.error(f'Error splitting PSMs for {fileroot}: {e}')
        return False

# -- _classifyPsmRow: returns the organism label for a single PSM row based on the protein ID column
def _classifyPsmRow(row: str, organism_tags: dict[str, str]) -> str:
    parts = row.rstrip('\n').split('\t')
    if not parts:
        return 'contaminants'
    protein_id = parts[-1]
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
        logMsg.error(f'Supplied organism tags {input_string} are invalid.')
        raise SystemExit(1)
    tags = {}
    for i in range(len(items)):
        if i % 2:
            tags.update({items[i-1]: items[i]})
    return tags