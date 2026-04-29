'''
Generates synthetic fixture files used in integration tests
'''

# -- Import external dependencies
import base64, struct, sys, zlib
from pathlib import Path
from typing import Optional

# -- Define variables
# Amino acid residue masses (monoisotopic)
RESIDUE_MASS: dict[str, float] = {
    'G': 57.02146, 'A': 71.03711, 'V': 99.06841, 'L': 113.08406, 'I': 113.08406,'P': 97.05276, 'F': 147.06841, 'W': 186.07931, 'M': 131.04049, 'S': 87.03203, 'T': 101.04768, 'C': 103.00919, 'Y': 163.06333, 'H': 137.05891, 'D': 115.02694, 'E': 129.04259, 'N': 114.04293, 'Q': 128.05858, 'K': 128.09496, 'R': 156.10111,
}
PROTON  = 1.007276
WATER   = 18.010565

# Synthetic proteome
PROTEINS: list[dict] = [
    {'id': 'SP|PROT1|GENE1', 'desc': 'Synthetic protein 1', 'seq': 'ACDEFGHIKLMNPQRSTVWYK',},
    {'id': 'SP|PROT2|GENE2', 'desc': 'Synthetic protein 2', 'seq': 'SAMPLEK',},
    {'id': 'SP|PROT3|GENE3', 'desc': 'Synthetic protein 3', 'seq': 'PEPTIDEFK',},
    {'id': 'SP|PROT4|GENE4', 'desc': 'Synthetic protein 4', 'seq': 'SYNTHETICR',},
    {'id': 'SP|PROT5|GENE5', 'desc': 'Synthetic protein 5', 'seq': 'VALIDATEK',},
]

# Tryptic peptides (protein_id, sequence)
TARGET_PEPTIDES: list[tuple[str, str]] = [
    ('SP|PROT1|GENE1', 'ACDEFGHIK'),
    ('SP|PROT1|GENE1', 'LMNPQR'),
    ('SP|PROT2|GENE2', 'SAMPLEK'),
    ('SP|PROT3|GENE3', 'PEPTIDEFK'),
    ('SP|PROT4|GENE4', 'SYNTHETICR'),
    ('SP|PROT5|GENE5', 'VALIDATEK'),
]

# -- Define mass calculation helper functions
def _peptide_mass(seq: str) -> float:
    '''Returns monoisotopic neutral mass of a peptide'''
    return sum(RESIDUE_MASS[aa] for aa in seq) + WATER

def _mz_precursor(seq: str, charge: int = 2) -> float:
    '''Returns [M+nH]n+ precursor m/z'''
    return (_peptide_mass(seq) + charge * PROTON) / charge

def _b_ions(seq: str) -> list[float]:
    '''Returns singly-charged b-ion series (b2 … b_{n-1}) for given sequence, skipping b1'''
    ions = []
    mass = 0.0
    for aa in seq[:-1]:
        mass += RESIDUE_MASS[aa]
        ions.append(mass + PROTON)
    return ions[1:]

def _y_ions(seq: str) -> list[float]:
    '''Returns singly-charged y-ion series (y2 … y_{n-1}), skipping y1'''
    ions = []
    mass = WATER
    for aa in reversed(seq[1:]):
        mass += RESIDUE_MASS[aa]
        ions.append(mass + PROTON)
    return ions[1:]

def _fragment_ions(seq: str) -> tuple[list[float], list[float]]:
    '''Returns (mz_list, intensity_list) for a simple b+y spectrum'''
    bs = _b_ions(seq)
    ys = _y_ions(seq)
    all_mz = bs + ys
    # Assign synthetic intensities: stronger towards centre of sequence
    n = len(all_mz)
    intensities = [1000.0 * (1.0 - abs(i / n - 0.5)) + 200.0 for i in range(n)]
    return all_mz, intensities

# -- Define mzML encoding helper functions
def _encode_array(values: list[float], dtype: str = 'f') -> str:
    '''
    Encode a list of floats as a zlib-compressed, base64-encoded binary array
    '''
    packed = struct.pack(f'<{len(values)}{dtype}', *values)
    compressed = zlib.compress(packed)
    return base64.b64encode(compressed).decode('ascii')

def _binary_data_array(values: list[float], array_type_cv: str) -> str:
    '''
    Return the XML fragment for one <binaryDataArray>
    '''
    encoded = _encode_array(values)
    # Calculate encoded length before base64
    n_bytes = len(base64.b64decode(encoded))
    # Recalculate the actual byte count from the raw packed+compressed data
    packed = struct.pack(f'<{len(values)}f', *values)
    n_bytes = len(zlib.compress(packed))
    return (
        f'      <binaryDataArray encodedLength="{len(encoded)}">\n'
        f'        <cvParam cvRef="MS" accession="MS:1000514" name="m/z array" unitAccession="MS:1000040" unitName="m/z" unitCvRef="MS"/>\n'
        f'        <cvParam cvRef="MS" accession="MS:1000515" name="intensity array" unitAccession="MS:1000131" unitName="number of detector counts" unitCvRef="MS"/>\n'
        f'        <cvParam cvRef="MS" accession="{array_type_cv}" name="{"m/z array" if "514" in array_type_cv else "intensity array"}"/>\n'
        f'        <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>\n'
        f'        <binary>{encoded}</binary>\n'
        f'      </binaryDataArray>\n'
    )

def _encode_array_nocompress(values: list[float]) -> str:
    packed = struct.pack(f'<{len(values)}f', *values)
    return base64.b64encode(packed).decode('ascii')

def _bda_nocompress(values: list[float], is_mz: bool) -> str:
    '''Binary data array block using uncompressed 32-bit floats (simpler for Crux)'''
    encoded = _encode_array_nocompress(values)
    if is_mz:
        type_acc  = 'MS:1000514'
        type_name = 'm/z array'
        unit_acc  = 'MS:1000040'
        unit_name = 'm/z'
    else:
        type_acc  = 'MS:1000515'
        type_name = 'intensity array'
        unit_acc  = 'MS:1000131'
        unit_name = 'number of detector counts'
    return (
        f'      <binaryDataArray encodedLength="{len(encoded)}">\n'
        f'        <cvParam cvRef="MS" accession="MS:1000521" name="32-bit float"/>\n'
        f'        <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>\n'
        f'        <cvParam cvRef="MS" accession="{type_acc}" name="{type_name}"'
        f' unitAccession="{unit_acc}" unitName="{unit_name}" unitCvRef="MS"/>\n'
        f'        <binary>{encoded}</binary>\n'
        f'      </binaryDataArray>\n'
    )

# -- Define synthetic FASTA writer function
def write_fasta(path: Path) -> Path:
    '''Write the synthetic proteome FASTA to given path and return the path'''
    lines = []
    for prot in PROTEINS:
        lines.append(f'>{prot["id"]} {prot["desc"]}')
        seq = prot['seq']
        # Wrap at 60 characters
        for i in range(0, len(seq), 60):
            lines.append(seq[i:i + 60])
    path.write_text('\n'.join(lines) + '\n')
    return path

# -- Define synthetic mzML writer function
def write_mzml(path: Path) -> Path:
    '''
    Write a minimal but valid indexed mzML 1.1.0 file to given path and return the path.
    '''
    spectra_blocks = []
    scan_idx = 1
    # MS1 survey scan
    # Place all precursor ions as peaks in a single MS1 spectrum.
    ms1_mz = sorted(_mz_precursor(seq, charge=2) for _, seq in TARGET_PEPTIDES)
    ms1_int = [5000.0] * len(ms1_mz)
    rt_ms1 = 10.0
    ms1_block = (
        f'    <spectrum index="{scan_idx - 1}" id="scan={scan_idx}" defaultArrayLength="{len(ms1_mz)}">\n'
        f'      <cvParam cvRef="MS" accession="MS:1000579" name="MS1 spectrum"/>\n'
        f'      <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>\n'
        f'      <cvParam cvRef="MS" accession="MS:1000130" name="positive scan"/>\n'
        f'      <cvParam cvRef="MS" accession="MS:1000127" name="centroid spectrum"/>\n'
        f'      <scanList count="1">\n'
        f'        <cvParam cvRef="MS" accession="MS:1000795" name="no combination"/>\n'
        f'        <scan>\n'
        f'          <cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{rt_ms1}" unitAccession="UO:0000010" unitName="second" unitCvRef="UO"/>\n'
        f'        </scan>\n'
        f'      </scanList>\n'
        f'      <binaryDataArrayList count="2">\n'
        + _bda_nocompress(ms1_mz, is_mz=True)
        + _bda_nocompress(ms1_int, is_mz=False)
        + f'      </binaryDataArrayList>\n'
        f'    </spectrum>\n'
    )
    spectra_blocks.append(ms1_block)
    scan_idx += 1
    # MS2 scans
    for pep_idx, (prot_id, seq) in enumerate(TARGET_PEPTIDES):
        prec_mz   = _mz_precursor(seq, charge=2)
        frag_mz, frag_int = _fragment_ions(seq)
        # Space scans 15s apart
        rt = 20.0 + pep_idx * 15.0
        ms2_block = (
            f'    <spectrum index="{scan_idx - 1}" id="scan={scan_idx}" defaultArrayLength="{len(frag_mz)}">\n'
            f'      <cvParam cvRef="MS" accession="MS:1000580" name="MSn spectrum"/>\n'
            f'      <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="2"/>\n'
            f'      <cvParam cvRef="MS" accession="MS:1000130" name="positive scan"/>\n'
            f'      <cvParam cvRef="MS" accession="MS:1000127" name="centroid spectrum"/>\n'
            f'      <scanList count="1">\n'
            f'        <cvParam cvRef="MS" accession="MS:1000795" name="no combination"/>\n'
            f'        <scan>\n'
            f'          <cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{rt}" unitAccession="UO:0000010" unitName="second" unitCvRef="UO"/>\n'
            f'        </scan>\n'
            f'      </scanList>\n'
            f'      <precursorList count="1">\n'
            f'        <precursor spectrumRef="scan=1">\n'
            f'          <selectedIonList count="1">\n'
            f'            <selectedIon>\n'
            f'              <cvParam cvRef="MS" accession="MS:1000744" name="selected ion m/z" value="{prec_mz:.6f}" unitAccession="MS:1000040" unitName="m/z" unitCvRef="MS"/>\n'
            f'              <cvParam cvRef="MS" accession="MS:1000041" name="charge state" value="2"/>\n'
            f'            </selectedIon>\n'
            f'          </selectedIonList>\n'
            f'          <activation>\n'
            f'            <cvParam cvRef="MS" accession="MS:1000422" name="beam-type collision-induced dissociation"/>\n'
            f'          </activation>\n'
            f'        </precursor>\n'
            f'      </precursorList>\n'
            f'      <binaryDataArrayList count="2">\n'
            + _bda_nocompress(frag_mz, is_mz=True)
            + _bda_nocompress(frag_int, is_mz=False)
            + f'      </binaryDataArrayList>\n'
            f'    </spectrum>\n'
        )
        spectra_blocks.append(ms2_block)
        scan_idx += 1
    total_spectra = len(spectra_blocks)
    mzml_content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<indexedmzML xmlns="http://psi.hupo.org/ms/mzml"\n'
        '             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '             xsi:schemaLocation="http://psi.hupo.org/ms/mzml '
        'http://psidev.info/files/ms/mzML/xsd/mzML1.1.2_idx.xsd">\n'
        '  <mzML>\n'
        '    <cvList count="2">\n'
        '      <cv id="MS" fullName="Proteomics Standards Initiative Mass Spectrometry Ontology" version="4.1.30" URI="https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo"/>\n'
        '      <cv id="UO" fullName="Unit Ontology" version="09:04:2014" URI="https://raw.githubusercontent.com/bio-ontology-research-group/unit-ontology/master/unit.obo"/>\n'
        '    </cvList>\n'
        '    <fileDescription>\n'
        '      <fileContent>\n'
        '        <cvParam cvRef="MS" accession="MS:1000579" name="MS1 spectrum"/>\n'
        '        <cvParam cvRef="MS" accession="MS:1000580" name="MSn spectrum"/>\n'
        '      </fileContent>\n'
        '    </fileDescription>\n'
        '    <softwareList count="1">\n'
        '      <software id="comMS_test_generator" version="1.0.0">\n'
        '        <cvParam cvRef="MS" accession="MS:1000799" name="custom unreleased software tool"/>\n'
        '      </software>\n'
        '    </softwareList>\n'
        '    <instrumentConfigurationList count="1">\n'
        '      <instrumentConfiguration id="IC1">\n'
        '        <cvParam cvRef="MS" accession="MS:1000031" name="instrument model"/>\n'
        '      </instrumentConfiguration>\n'
        '    </instrumentConfigurationList>\n'
        '    <dataProcessingList count="1">\n'
        '      <dataProcessing id="dp1">\n'
        '        <processingMethod order="0" softwareRef="comMS_test_generator">\n'
        '          <cvParam cvRef="MS" accession="MS:1000544" name="Conversion to mzML"/>\n'
        '        </processingMethod>\n'
        '      </dataProcessing>\n'
        '    </dataProcessingList>\n'
        f'    <run id="synthetic_run">\n'
        f'      <spectrumList count="{total_spectra}" defaultDataProcessingRef="dp1">\n'
        + ''.join(spectra_blocks)
        + '      </spectrumList>\n'
        '    </run>\n'
        '  </mzML>\n'
        '  <indexList count="1">\n'
        '    <index name="spectrum"/>\n'
        '  </indexList>\n'
        '</indexedmzML>\n'
    )
    path.write_text(mzml_content, encoding='utf-8')
    return path

# Define generator function
def generate_all(out_dir: Optional[Path] = None) -> tuple[Path, Path]:
    '''
    Generate both fixture files into given out directory, defaulting to script's parent directory, returning (fasta_path, mzml_path)
    '''
    if out_dir is None:
        out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    fasta = write_fasta(out_dir / 'synthetic_proteome.fasta')
    mzml = write_mzml(out_dir / 'synthetic.mzML')
    return fasta, mzml

# Define entrypoint
if __name__ == '__main__':
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    fasta, mzml = generate_all(d)
    print(f'Synthetic proteome FASTA saved to: {fasta}')
    print(f'Synthetic mzML file saved to: {mzml}')
