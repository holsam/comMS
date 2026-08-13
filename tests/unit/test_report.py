'''
Unit tests for helper functions in src/comms/commands/report.py
'''

# -- Import external dependencies
import json, pytest
from pathlib import Path
from unittest.mock import patch

# -- Import functions under test
from comms.commands.report import (
    _log_organism_outcomes,
    _read_status,
    _resolve_r_script,
    _section_status,
    _write_index,
    run_report,
)

def _assert_config_sidecar(out_dir: Path, command: str, overrides_given: bool, expect_key: tuple[str, str] | None = None, expect_value=None):
    sidecar = out_dir / f'{command}.config.toml'
    if not overrides_given:
        assert not sidecar.exists()
        return
    assert sidecar.exists()
    import tomllib
    with sidecar.open('rb') as f:
        cfg = tomllib.load(f)
    if expect_key:
        section, key = expect_key
        assert cfg[section][key] == expect_value

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
        _write_index(tmp_path, {'quantify_dir': '/tmp/q'}, {'qc': 'succeeded', 'da': 'failed'}, {'qc': {'org1': 'succeeded', 'org2': 'failed'}})
        assert (tmp_path / 'index.md').exists()

    def test_index_contains_section_names(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': 'succeeded', 'da': 'failed'}, {'qc': {'org1': 'succeeded', 'org2': 'failed'}})
        content = (tmp_path / 'index.md').read_text()
        assert 'qc' in content
        assert 'da' in content

    def test_failed_section_marked_with_failed(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': 'failed'}, {'qc': {'org1': 'failed', 'org2': 'failed'}})
        assert 'FAILED' in (tmp_path / 'index.md').read_text()

    def test_passed_section_marked_with_checkmark(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': 'succeeded'}, {'qc': {'org1': 'succeeded', 'org2': 'succeeded'}})
        assert '✓' in (tmp_path / 'index.md').read_text()

    def test_parameters_included_in_index(self, tmp_path):
        _write_index(tmp_path, {'organism_prefix': 'Mtrun'}, {}, {})
        assert 'organism_prefix' in (tmp_path / 'index.md').read_text()

    def test_partial_status_glyph(self, tmp_path):
        _write_index(tmp_path, {}, {'da': 'partial'}, {'da': {'Mt': 'ok', 'Ri': 'failed'}})
        assert 'PARTIAL' in (tmp_path / 'index.md').read_text()

    def test_skipped_status_glyph(self, tmp_path):
        _write_index(tmp_path, {}, {'qc': 'skipped'}, {})
        assert 'SKIPPED' in (tmp_path / 'index.md').read_text()

    def test_per_organism_lines_nested_under_section(self, tmp_path):
        _write_index(tmp_path, {}, {'da': 'partial'}, {'da': {'Mt': 'ok', 'Ri': 'failed'}})
        content = (tmp_path / 'index.md').read_text()
        da_line_index = content.index('- da:')
        mt_line_index = content.index('Mt: ok')
        assert mt_line_index > da_line_index


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
        top_n=20,
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
                top_n=20,
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
                top_n=20,
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
                top_n=20,
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

    def test_override_writes_report_config_sidecar(self, tmp_path, experiment_ctx):
        _run_report_with_mocks(tmp_path, experiment_ctx, sections=['qc'], lfc_threshold=2.0)
        sidecar = experiment_ctx.root / 'comms/results/report/report.config.toml'
        assert sidecar.exists()
        import tomllib
        with sidecar.open('rb') as f:
            cfg = tomllib.load(f)
        assert cfg['report']['lfc_threshold'] == 2.0

    def test_no_override_writes_no_sidecar(self, tmp_path, experiment_ctx):
        defaults = dict(
            quantify_dir=_make_quantify_dir(tmp_path), sample_sheet=_make_sample_sheet(tmp_path),
            ctx=experiment_ctx, lfq_dir=None, ref_info=None, cont_csv=None,
            organism_prefix='Mtrun', min_reps=None, lfc_threshold=None,
            fdr_threshold=None, top_n=None, overwrite=True, rscript='Rscript', in_pipeline=False,
        )
        with patch('comms.commands.report._run_r_section', return_value=True), patch('shutil.which', return_value='/usr/bin/Rscript'):
            run_report(sections=['qc'], **defaults)
        sidecar = experiment_ctx.root / 'comms/results/report/report.config.toml'
        assert not sidecar.exists()

    def test_lfq_dir_falls_back_to_conventional_location(self, tmp_path, experiment_ctx):
        lfq_dir = experiment_ctx.root / 'comms/results/lfq'
        lfq_dir.mkdir(parents=True)
        mock_run = _run_report_with_mocks(tmp_path, experiment_ctx, sections=['concordance'], lfq_dir=None)
        called = [c.kwargs['section'] for c in mock_run.call_args_list]
        assert 'concordance' in called

    def test_ref_info_falls_back_to_context_value(self, tmp_path, experiment_ctx):
        ref = tmp_path / 'ref.txt'
        ref.touch()
        experiment_ctx.metadata['report'] = {'ref_info': str(ref)}
        _run_report_with_mocks(tmp_path, experiment_ctx, sections=['qc'], ref_info=None)   # should not raise

class TestReadStatus:
    def test_missing_file_returns_empty_dicts(self, tmp_path):
        assert _read_status(tmp_path) == ({}, {})

    def test_malformed_json_returns_empty_dicts(self, tmp_path):
        (tmp_path / '_status.json').write_text('{not valid json')
        assert _read_status(tmp_path) == ({}, {})

    def test_well_formed_file_parsed(self, tmp_path):
        (tmp_path / '_status.json').write_text(json.dumps({
            'organisms': {'Mt': 'ok', 'Ri': 'failed'},
            'reasons': {'Ri': 'insufficient replicates'},
        }))
        organisms, reasons = _read_status(tmp_path)
        assert organisms == {'Mt': 'ok', 'Ri': 'failed'}
        assert reasons == {'Ri': 'insufficient replicates'}

    def test_unrecognised_status_values_dropped(self, tmp_path):
        (tmp_path / '_status.json').write_text(json.dumps({
            'organisms': {'Mt': 'ok', 'Ri': 'bogus_status'},
            'reasons': {},
        }))
        organisms, _ = _read_status(tmp_path)
        assert organisms == {'Mt': 'ok'}

class TestSectionStatus:
    def test_no_organisms_proc_ok_true_is_skipped(self):
        assert _section_status(proc_ok=True, organisms={}) == 'skipped'

    def test_no_organisms_proc_ok_false_is_failed(self):
        assert _section_status(proc_ok=False, organisms={}) == 'failed'

    def test_all_ok_is_succeeded(self):
        assert _section_status(True, {'Mt': 'ok', 'Ri': 'ok'}) == 'succeeded'

    def test_mixed_ok_and_failed_is_partial(self):
        assert _section_status(True, {'Mt': 'ok', 'Ri': 'failed'}) == 'partial'

    def test_all_failed_is_failed(self):
        assert _section_status(True, {'Mt': 'failed', 'Ri': 'failed'}) == 'failed'

    def test_all_skipped_none_ok_or_failed_is_skipped(self):
        assert _section_status(True, {'Mt': 'skipped', 'Ri': 'skipped'}) == 'skipped'

class TestLogOrganismOutcomes:
    def test_logs_one_line_per_organism(self, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            _log_organism_outcomes('da', {'Mt': 'ok', 'Ri': 'failed'}, {})
        assert 'Mt' in caplog.text and 'Ri' in caplog.text

    def test_includes_reason_when_present(self, caplog):
        import logging
        with caplog.at_level(logging.WARN):
            _log_organism_outcomes('da', {'Ri': 'failed'}, {'Ri': 'insufficient replicates'})
        assert 'insufficient replicates' in caplog.text

    def test_omits_parenthetical_when_no_reason(self, caplog):
        import logging
        with caplog.at_level(logging.WARN):
            _log_organism_outcomes('da', {'Mt': 'ok'}, {})
        assert '()' not in caplog.text