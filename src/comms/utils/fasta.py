'''
comMS FASTA file utility functions
'''
# -- Import external dependencies
import re
from pathlib import Path

# -- Import internal dependencies
from comms.utils.log import logMsg

# -- readFasta: returns dictionary of lists containing strings corresponding to FASTA header and sequence
def readFasta(fasta: Path) -> list[str, str]:
    fasta_text = [string for string in fasta.read_text().split('>') if string]
    fasta_entries = []
    for string in fasta_text:
        lines = string.split('\n')
        header = lines[0]
        sequence = ''.join(line for line in lines[1:])
        fasta_entries.append([header, sequence])
    return fasta_entries

# -- writeFasta: returns None, but writes a file to specified Path containing data in FASTA format
def writeFasta(data: list, out_file: Path):
    with open(out_file, "w") as f:
        for entry in data:
            f.write(f'>{entry[0]}\n{entry[1]}\n')

# -- _searchHeaderForTag: returns boolean corresponding to whether an entry's header contained any known organism tags, if True also updates subfastas with entry
def _searchHeaderForTag(subfastas: dict, organism_tags: dict[str, str], entry: list[str, str]) -> bool:
    for key in organism_tags.keys():
        if re.search(organism_tags[key], entry[0]):
            if key in subfastas.keys():
                subfastas[key].append(entry)
            else:
                subfastas.update({key: [entry]})
            return True
    return False

# -- splitFastaByOrganism: returns dictionary of strings mapped to Paths corresponding to organism-specific FASTA files
def splitFastaByOrganism(fasta_path: Path, out_dir: Path, organism_tags: dict[str, str]) -> dict[str, Path]:
    '''Partition a combined FASTA into per-organism sub-FASTAs'''
    subfastas = {}
    fasta = readFasta(fasta_path)
    logMsg.debug(f'Read FASTA from {fasta_path}')
    # Split FASTA file into organism-specific and contaminant sub-FASTAs
    for entry in fasta:
        if _searchHeaderForTag(subfastas, organism_tags, entry):
            continue
        if 'contaminants' in subfastas.keys():
            subfastas['contaminants'].append(entry)
        else:
            subfastas.update({'contaminants': [entry]})
    # Add all contaminants to each organism
    if 'contaminants' in subfastas.keys():
        for contaminant in subfastas['contaminants']:
            for subfasta_key in [key for key in subfastas.keys() if key != 'contaminants']:
                subfastas[subfasta_key].append(contaminant)
        # Remove contaminants sub-FASTA now it's been added to all others
        del subfastas['contaminants']
    logMsg.debug(f'Partitioned into {len(subfastas)} organisms')
    # Write all sub-FASTAs
    outputs = {}
    for subfasta_key in subfastas.keys():
        out_file = out_dir / f"{subfasta_key}.fa"
        writeFasta(data=subfastas[subfasta_key], out_file=out_file)
        logMsg.debug(f'Wrote organism FASTA: {out_file}')
        outputs.update({subfasta_key: out_file})
    # Return dictionary of strings
    return outputs
