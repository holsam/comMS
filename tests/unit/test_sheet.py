'''
Unit tests for src/comms/utils/sheet.py
'''
from comms.utils.sheet import SampleRow, render_sample_sheet, parse_sample_sheet


class TestRenderSampleSheet:
    def test_header_uses_canonical_column_order(self):
        text = render_sample_sheet([])
        assert text.splitlines()[0] == 'sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch'

    def test_row_renders_tab_joined(self):
        row = SampleRow(sample_id='S1', raw_file='s1.RAW', treatment='MOCK', fraction='WCL', replicate=1, batch='A')
        text = render_sample_sheet([row])
        assert 'S1\ts1.RAW\tMOCK\tWCL\t1\tA' in text

    def test_none_replicate_renders_empty(self):
        row = SampleRow(sample_id='S1', raw_file='s1.RAW', replicate=None)
        text = render_sample_sheet([row])
        assert '\t\t' in text.splitlines()[1] or text.splitlines()[1].endswith('\t')

    def test_trailing_newline(self):
        row = SampleRow(sample_id='S1', raw_file='s1.RAW')
        assert render_sample_sheet([row]).endswith('\n')

    def test_empty_rows_still_writes_header(self):
        text = render_sample_sheet([])
        assert len(text.splitlines()) == 1


class TestParseSampleSheet:
    def test_round_trips_with_render(self):
        row = SampleRow(sample_id='S1', raw_file='s1.RAW', treatment='MOCK', fraction='WCL', replicate=2, batch='A')
        text = render_sample_sheet([row])
        parsed = parse_sample_sheet(text)
        assert len(parsed) == 1
        assert parsed[0].sample_id == 'S1'
        assert parsed[0].replicate == 2

    def test_empty_text_returns_empty_list(self):
        assert parse_sample_sheet('') == []

    def test_numeric_replicate_sets_overridden_true(self):
        text = 'sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch\nS1\ts1.RAW\tMOCK\tWCL\t3\tA\n'
        parsed = parse_sample_sheet(text)
        assert parsed[0].replicate == 3
        assert parsed[0].replicate_overridden is True

    def test_empty_replicate_parses_to_none(self):
        text = 'sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch\nS1\ts1.RAW\tMOCK\tWCL\t\tA\n'
        parsed = parse_sample_sheet(text)
        assert parsed[0].replicate is None
        assert parsed[0].replicate_overridden is False

    def test_whitespace_stripped_from_fields(self):
        text = 'sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch\n S1 \t s1.RAW \tMOCK\tWCL\t1\tA\n'
        parsed = parse_sample_sheet(text)
        assert parsed[0].sample_id == 'S1'

    def test_missing_batch_column_defaults_to_empty(self):
        text = 'sample_id\traw_file\ttreatment\tfraction\treplicate\nS1\ts1.RAW\tMOCK\tWCL\t1\n'
        parsed = parse_sample_sheet(text)
        assert parsed[0].batch == ''