'''
comMS motif extension: inputs utility tests
'''

# -- Import external dependencies
import pytest
from openpyxl import Workbook
from pathlib import Path

# Import motif/utils/inputs.py
from comms.ext.motif.utils import inputs

# -- Define test class for inputs

class TestMotifInputs():
    def test_apply_window():
        seq = 'M' + 'A' * 100
        assert inputs.apply_window(seq, "full", None) == seq
        assert inputs.apply_window(seq, "n_terminal_60", None) == seq[:60]
        assert inputs.apply_window(seq, "n_terminal_after_sp", 20) == seq[20:80]
        assert inputs.apply_window(seq, "n_terminal_after_sp", None) == seq     # fall back

    def test_resolve_from_report_da(tmp_path, monkeypatch):
        wb = Workbook()
        ws = wb.active
        ws.title = 'example_treat_vs_mock'
        ws.append(['protein_id', 'direction'])
        for pid, d in [('a', 'Up'), ('b', 'Down'), ('c', 'Unchanged')]:
            ws.append([pid, d])
        (tmp_path / 'comms/results/report/da').mkdir(parents=True)
        wb.save(tmp_path / 'comms/results/report/da' / 'da_summary.xlsx')
        fg, bg, src = inputs.resolve_from_report_da(tmp_path, 'ev_myc_vs_mock', 'detected-unchanged', None)
        assert set(fg) == {'a', 'b'} and bg == ['c']