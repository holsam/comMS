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
    source_path: str = ''

# -- render_sample_sheet: build the TSV text for a list of SampleRow
def render_sample_sheet(rows) -> str:
    lines = ['\t'.join(COLUMNS)]
    for r in rows:
        replicate = '' if r.replicate is None else str(r.replicate)
        lines.append('\t'.join(
            [r.sample_id, r.raw_file, r.treatment, r.fraction, replicate, r.batch]
        ))
    return '\n'.join(lines) + '\n'

# -- parse_sample_sheet: parse a TSV text into a list of SampleRow
def parse_sample_sheet(text: str) -> list['SampleRow']:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split('\t')]
    rows: list[SampleRow] = []
    for line in lines[1:]:
        values = line.split('\t')
        record = dict(zip(header, values))
        replicate_text = record.get('replicate', '').strip()
        rows.append(SampleRow(
            sample_id=record.get('sample_id', '').strip(),
            raw_file=record.get('raw_file', '').strip(),
            treatment=record.get('treatment', '').strip(),
            fraction=record.get('fraction', '').strip(),
            replicate=int(replicate_text) if replicate_text else None,
            batch=record.get('batch', '').strip(),
            replicate_overridden=bool(replicate_text),
        ))
    return rows