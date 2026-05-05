'''
comMS rescore functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.fasta import splitFastaByOrganism
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_rescore: rescores all Tide-search PSM files in input_dir using Percolator and writes results to output
def run_rescore(input_dir: Path, database: Path, output: Path, org_tags: str, in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('rescore')
        log.debug('Starting rescore command')
    
    logMsg.debug('Locating Crux binary')
    bin_dir = pathutil.repoBinDir()
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        logMsg.error(f'Crux binary not found under: {bin_dir}')
        print(f'[bold red]ERROR:[/bold red] Crux binary not found under {bin_dir}.')
        raise SystemExit(1)
    
    logMsg.debug(f'Scanning for Tide-search PSM files in: {input_dir}')
    target_files = sorted(input_dir.glob('*.tide-search.target.txt'))
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
            organism_tags = _parseOrganismTags(config['organism'])
        else:
            logMsg.error(f'No organism tag data found in user config file.')
            print(f'[bold red]ERROR:[/bold red] No organism tag data found in user config file. Set for one command only using [italic]--organism-tags[/] or set in user config.')
            raise SystemExit(1)
    
    out_dir = pathutil.generateOutputFileStructure(output, 'rescore')
    log_path = out_dir / 'rescore.log'
    
    sub_fastas = splitFastaByOrganism(database, organism_tags, out_dir)
    
    print(f'\nRescoring {len(target_files)} PSM file(s) with Percolator using {len(sub_fastas)} organism database(s)...')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for label, sub_fasta in sub_fastas.items():
            for target_file in tqdm(target_files, desc='Files rescored'):
                fileroot = target_file.name.removesuffix('.tide-search.target.txt')
                filename = f'{fileroot}.{label}'
                ok = cruxutil.percolator(
                    crux_bin=crux_bin,
                    target_psm_file=target_file,
                    database=sub_fasta,
                    out_dir=out_dir / label,
                    fileroot=filename,
                    config=config,
                )
                if ok:
                    n_ok += 1
                    logMsg.debug(f'Percolator output written to: {out_dir / label / filename}.percolator.target.psms.txt')
                else:
                    logMsg.warn(f'Percolator failed for: {target_file.name} using {label}')
                    n_fail += 1
    logMsg.info(f'Rescoring completed — {n_ok} succeeded, {n_fail} failed')
    if n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] rescoring failed for {n_fail} file(s). Check {log_path} for details.')

    logMsg.debug(f'Merging organism-specific PSM files')
    merge_n_ok, merge_n_fail = 0, 0
    for target_file in tqdm(target_files, desc='Files merged'):
        file_base = target_file.name.removesuffix('.tide-search.target.txt')
        ok = _mergeRescoredPsms(file_base, sub_fastas, out_dir)
        if ok:
            merge_n_ok +=1
            logMsg.debug(f'Percolator output for {file_base} merged to {out_dir / file_base}.percolato.(target/decoy).psms.txt')
        else:
            logMsg.warn(f'Percolator output for {file_base} could not be merged')
            merge_n_fail += 1
    logMsg.info(f'Rescored PSM merging completed - {merge_n_ok} succeeded, {merge_n_fail} failed')
    if merge_n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] merging failed for {n_fail} file(s). Check {log_path} for details.')
    
    print(f'\n[bold green]Rescore finished successfully - summary:[/]')
    print(f'- Files rescored successfully: {n_ok}')
    print(f'- Files failed: {n_fail}')
    print(f'- Output directory: {out_dir}\n')

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

# -- _mergeRescoredPsms: returns True, but writes concatenated PSM files to output directory
def _mergeRescoredPsms(file_base, subfastas, out_dir):
    try:
        types = ['target', 'decoy']
        for type in types:
            merged_data = _mergeTypeRescoredPsms(type, file_base, subfastas, out_dir)
            out_file = out_dir / f'{file_base}.percolator.{type}.psms.txt'
            with open(out_file, 'w') as f:
                f.writelines(merged_data)
        return True
    except Exception:
        return False

# -- _mergeTypeRescoredPsms: returns list of string corresponding to concatenated lines of organism-specific rescored PSMs
def _mergeTypeRescoredPsms(match_type: str, file_base: str, subfastas, out_dir):
    data = []
    for label in subfastas.keys():
        label_data = []
        file = out_dir / label / f'{file_base}.{label}.percolator.{match_type}.psms.txt'
        with open(file, 'r') as f:
            if not data:
                header = f'organism\t{f.readline()}'
                data.append(header)
            label_data.extend(f.readlines()[1:])
        for i in range(len(label_data)):
            label_data[i] = f'{label}\t{label_data[i]}'
        data.extend(label_data)
    for i in range(len(data)):
        if not data[i].endswith('\n'):
            data[i] = f'{data[i]}\n'
    return data