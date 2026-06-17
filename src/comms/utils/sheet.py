'''
comMS sample-sheet data model and rendering
'''

# -- Import external dependencies
from dataclasses import dataclass

# -- Column layout mirrors the sample-sheet schema
COLUMNS = ['sample_id', 'raw_file', 'treatment', 'fraction', 'replicate', 'batch']
COL_SAMPLE_ID, COL_RAW, COL_TREATMENT, COL_FRACTION, COL_REPLICATE, COL_BATCH = range(6)

# -- Display labels differ from the written column names
HEADER_LABELS = {'batch': 'batch (optional)'}

# -- Define dataclass SampleRow to hold a sample sheet row
@dataclass
class SampleRow:
    sample_id: str
    raw_file: str
    treatment: str = ''
    fraction: str = ''
    replicate: int | None = None
    batch: str = ''
    replicate_overridden: bool = False

# -- render_sample_sheet: build the TSV text for a list of SampleRow
def render_sample_sheet(rows) -> str:
    lines = ['\t'.join(COLUMNS)]
    for r in rows:
        replicate = '' if r.replicate is None else str(r.replicate)
        lines.append('\t'.join(
            [r.sample_id, r.raw_file, r.treatment, r.fraction, replicate, r.batch]
        ))
    return '\n'.join(lines) + '\n'