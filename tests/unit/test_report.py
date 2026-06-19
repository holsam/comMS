'''
Unit tests for helper functions in src/comms/commands/report.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path
from unittest.mock import patch

# -- Import functions under test
from comms.commands.report import _resolve_r_script, _write_index, run_report

# -- Define tests for resolving R script paths
class TestResolveRScript:
    def test_returns_path(self):
        result = _resolve_r_script('qc.R')
        assert isinstance(result, Path)

    def test_path_ends_with_script_name(self):
        result = _resolve_r_script('da.R')
        assert result.name == 'da.R'

    def test_aux_script_resolved(self):
        result = _resolve_r_script('aux/ev-markers.R')
        assert isinstance(result, Path)
        assert result.name == 'ev-markers.R'

# -- Define tests for writing index
class TestWriteIndex:
    def test_creates_index_file(self, tmp_path):
        _write_index(tmp_path, {'quantify_dir': '/tmp/q'}, {'qc': True, 'da': False})
        assert (tmp_path / 'index.md').exists()

    def test_index_contains_section_names(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': True, 'da': False})
        content = (tmp_path / 'index.md').read_text()
        assert 'qc' in content
        assert 'da' in content

    def test_failed_section_marked_with_failed(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': False})
        assert 'FAILED' in (tmp_path / 'index.md').read_text()

    def test_passed_section_marked_with_checkmark(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': True})
        assert '✓' in (tmp_path / 'index.md').read_text()

    def test_parameters_included_in_index(self, tmp_path):
        _write_index(tmp_path, {'organism_prefix': 'Mtrun'}, {})
        assert 'organism_prefix' in (tmp_path / 'index.md').read_text()

# -- Define shared fixtures
# -- _make_quantify_dir: returns Path to example quantify output
def _make_quantify_dir(tmp_path: Path) -> Path:
    d = tmp_path / 'comms/results/quantify'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'sample1.spectral-counts.target.txt').write_text(
        'ProteinId\tProteinGroupId\tq-value\tpeptideIds\tspec_count_all\n'
        'Mtrun001\tMtrun001\t0.001\tPEP1 PEP2\t5\n'
    )
    return d
# _make_sample_sheet: returns Path to example sample sheet
def _make_sample_sheet(tmp_path: Path) -> Path:
    p = tmp_path / 'comms/sample_sheet.tsv'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        'sample_id\traw_file\ttreatment\tfraction\treplicate\n'
        'S1\tsample1.RAW\tmock\tEV\t1\n'
        'S2\tsample2.RAW\tmyc\tEV\t1\n'
    )
    return p
# _run_report_with_mocks: returns None but runs report function
def _run_report_with_mocks(tmp_path, experiment_ctx, sections, **kwargs):
    defaults = dict(
        quantify_dir=_make_quantify_dir(tmp_path),
        sample_sheet=_make_sample_sheet(tmp_path),
        ctx=experiment_ctx,
        lfq_dir=None,
        ref_info=None,
        cont_csv=None,
        organism_prefix='Mtrun',
        min_reps=2,
        lfc_threshold=1.0,
        fdr_threshold=0.05,
        overwrite=True,
        rscript='Rscript',
        in_pipeline = False,
    )
    defaults.update(kwargs)
    with patch('comms.commands.report._run_r_section', return_value=True) as mock_run, patch('shutil.which', return_value='/usr/bin/Rscript'):
        run_report(sections=sections, **defaults)
    return mock_run

# -- Define tests for validating run_report function
class TestRunReportValidation:
    def test_raises_when_no_spectral_count_files(self, tmp_path, experiment_ctx):
        empty = tmp_path / 'empty'; empty.mkdir()
        ss = _make_sample_sheet(tmp_path)
        with patch('shutil.which', return_value='/usr/bin/Rscript'), pytest.raises(SystemExit):
            run_report(
                quantify_dir=empty,
                sample_sheet=ss,
                ctx=experiment_ctx,
                lfq_dir=None,
                ref_info=None,
                cont_csv=None,
                organism_prefix='Mtrun',
                min_reps=2,
                lfc_threshold=1.0,
                fdr_threshold=0.05,
                sections=['qc'],
                overwrite=True,
                rscript='Rscript',
                in_pipeline = False,
            )

    def test_raises_when_output_exists_without_overwrite(self, tmp_path, experiment_ctx):
        qd = _make_quantify_dir(tmp_path); ss = _make_sample_sheet(tmp_path)
        out = experiment_ctx.root / 'comms/results/report'
        out.mkdir(parents=True, exist_ok=True)
        with patch('shutil.which', return_value='/usr/bin/Rscript'), pytest.raises(SystemExit):
            run_report(
                quantify_dir=qd,
                sample_sheet=ss,
                ctx=experiment_ctx,
                lfq_dir=None,
                ref_info=None,
                cont_csv=None,
                organism_prefix='Mtrun',
                min_reps=2,
                lfc_threshold=1.0,
                fdr_threshold=0.05,
                sections=['qc'],
                overwrite=False,
                rscript='Rscript',
                in_pipeline = False,
            )

    def test_raises_when_rscript_not_found(self, tmp_path, experiment_ctx):
        qd = _make_quantify_dir(tmp_path); ss = _make_sample_sheet(tmp_path)
        with patch('shutil.which', return_value=None), pytest.raises(SystemExit):
            run_report(
                quantify_dir=qd,
                sample_sheet=ss,
                ctx=experiment_ctx,
                lfq_dir=None, 
                ref_info=None,
                cont_csv=None,
                organism_prefix='Mtrun',
                min_reps=2,
                lfc_threshold=1.0,
                fdr_threshold=0.05,
                sections=['qc'],
                overwrite=True,
                rscript='Rscript',
                in_pipeline = False,
            )

    def test_concordance_dropped_without_lfq_dir(self, tmp_path, experiment_ctx):
        mock_run = _run_report_with_mocks(tmp_path, experiment_ctx, sections=['qc', 'concordance'])
        called = [c.kwargs['section'] for c in mock_run.call_args_list]
        assert 'concordance' not in called
        assert 'qc' in called

    def test_creates_output_directory(self, tmp_path, experiment_ctx):
        _run_report_with_mocks(tmp_path, experiment_ctx, sections=['qc'])
        out = experiment_ctx.root / 'comms/results/report'
        assert out.exists()

    def test_writes_index_file(self, tmp_path, experiment_ctx):
        _run_report_with_mocks(tmp_path, experiment_ctx, sections=['qc'])
        out = experiment_ctx.root / 'comms/results/report'
        assert (out / 'index.md').exists()

    def test_da_section_receives_lfc_and_fdr_as_positional_args(self, tmp_path, experiment_ctx):
        mock_run = _run_report_with_mocks(
            tmp_path, experiment_ctx, sections=['da'], lfc_threshold=0.585, fdr_threshold=0.1
        )
        da_call = next(c for c in mock_run.call_args_list if c.kwargs.get('section') == 'da')
        args = da_call.kwargs['positional_args']
        assert '0.585' in args
        assert '0.1' in args

    def test_logger_named_report(self, tmp_path, experiment_ctx):
        from comms.utils.log import logMsg
        _run_report_with_mocks(tmp_path, experiment_ctx, sections=['qc'])
        assert logMsg._instance.logger.name == 'report'