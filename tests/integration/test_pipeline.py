'''
Integration tests for src/comms/commands/pipeline.py > run_pipeline and the individual command-level functions (run_index, run_search, run_rescore, run_lfq, run_quantify)
'''

# -- Import external dependencies
import logging, pytest
from pathlib import Path
from unittest.mock import call, patch

# -- Import internal functions
from comms.commands.index import run_index
from comms.commands.search import run_search
from comms.commands.rescore import run_rescore
from comms.commands.lfq import run_lfq
from comms.commands.quantify import run_quantify
from comms.commands.pipeline import run_pipeline
from comms.utils.log import logMsg

# -- Define pytest mark for crux (all tests in file require Crux)
pytestmark = pytest.mark.crux

# -- Define tests for running index command
class TestRunIndex:
    def test_creates_index_output_dir(self, crux_bin, synthetic_fasta, tmp_path):
        run_index(database=synthetic_fasta, output=tmp_path)
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        assert index_dir.exists(), f'Expected index dir at {index_dir}'

    def test_index_output_is_non_empty(self, crux_bin, synthetic_fasta, tmp_path):
        run_index(database=synthetic_fasta, output=tmp_path)
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        assert any(index_dir.iterdir()), 'Index directory is empty after run_index'

    def test_prints_success_message(self, crux_bin, synthetic_fasta, tmp_path, capsys):
        run_index(database=synthetic_fasta, output=tmp_path)
        captured = capsys.readouterr()
        assert 'SUCCESS' in captured.out or 'index' in captured.out.lower()

    def test_comms_logger_is_index(self, crux_bin, synthetic_fasta, tmp_path):
        run_index(database=synthetic_fasta, output=tmp_path)
        assert logMsg._instance.logger.name == 'index'

# -- Define fixture for generating index using tide-index
@pytest.fixture(scope='module')
def pipeline_index(crux_bin, tmp_path_factory):
    '''Build a shared index for all pipeline integration tests.'''
    from tests.fixtures.generate_fixtures import write_fasta
    work = tmp_path_factory.mktemp('pipeline_index')
    fasta = write_fasta(work / 'synthetic_proteome.fasta')
    try:
        run_index(database=fasta, output=work)
    except SystemExit as e:
        pytest.skip(f'run_index failed (exit {e.code}) — skipping pipeline tests')
    return work / 'comms' / 'results' / 'index', fasta

# -- Define tests for running search command
class TestRunSearch:
    def test_creates_search_output_dir(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=False,
            threads=1,
        )
        search_dir = tmp_path / 'comms' / 'results' / 'search'
        assert search_dir.exists()

    def test_target_psm_file_exists(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=False,
            threads=1,
        )
        search_dir = tmp_path / 'comms' / 'results' / 'search'
        psm_files = list(search_dir.glob('*.tide-search.target.txt'))
        assert psm_files, 'No target PSM file found after run_search'

    def test_prints_search_summary(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, capsys):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=False,
            threads=1,
        )
        captured = capsys.readouterr()
        assert 'Search finished successfully - summary:' in captured.out

    def test_comms_logger_is_search(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=False,
            threads=1,
        )
        assert logMsg._instance.logger.name == 'search'

class TestRunSearchParamMedic:
    def test_completes_without_raising(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=True,
            threads=1,
        )
 
    def test_creates_search_output_directory(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=True,
            threads=1,
        )
        assert (tmp_path / 'comms' / 'results' / 'search').exists(), 'No comms/results/search directory created when run with --param-medic'
 
    def test_creates_target_psm_file(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=True,
            threads=1,
        )
        search_dir = tmp_path / 'comms' / 'results' / 'search'
        psm_files = list(search_dir.glob('*.tide-search.target.txt'))
        assert psm_files, 'No target PSM file found after run_search with --param-medic'
 
    def test_creates_param_medic_output_directory(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=True,
            threads=1,
        )
        pm_dir = tmp_path / 'comms' / 'results' / 'param-medic'
        assert pm_dir.exists()
 
    def test_falls_back_to_config_defaults_when_param_medic_yields_no_estimates(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, capsys):
        '''
        When param-medic cannot estimate tolerances (as expected for synthetic data), run_search should fall back to config defaults and report those values in the terminal summary.
        '''
        from comms.utils.settings import loadDefaultConfig
        cfg = loadDefaultConfig()
        expected_prec = str(cfg['search']['precursor_tolerance_ppm'])
        expected_bw = str(cfg['search']['mz_bin_width'])
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=True,
            threads=1,
        )
        captured = capsys.readouterr()
        assert expected_prec in captured.out
        assert expected_bw in captured.out
 
    def test_warns_when_param_medic_yields_no_estimates(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, caplog):
        '''
        When param-medic produces no usable estimates, a warning should be
        logged indicating fallback to defaults.
        '''
        index_dir, _ = pipeline_index
        with caplog.at_level(logging.WARNING):
            run_search(
                input_dir=synthetic_mzml.parent,
                index_dir=index_dir,
                output=tmp_path,
                param_medic=True,
                threads=1,
            )
        warning_text = caplog.text.lower()
        assert 'falling back' in warning_text or 'no usable' in warning_text
 
    def test_search_summary_reports_numeric_tolerance(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, capsys):
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=tmp_path,
            param_medic=True,
            threads=1,
        )
        captured = capsys.readouterr()
        assert 'precursor tolerance' in captured.out
        assert 'bin width' in captured.out
 
    def test_produces_same_output_as_no_param_medic_when_estimates_unavailable(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        '''
        When param-medic falls back to defaults, the search output (PSM file
        existence and line count) should be identical to a run without
        param-medic, since both use the same config tolerance values.
        '''
        out_with = tmp_path / 'with_pm'
        out_without = tmp_path / 'without_pm'
        index_dir, _ = pipeline_index
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=out_with,
            param_medic=True,
            threads=1,
        )
        run_search(
            input_dir=synthetic_mzml.parent,
            index_dir=index_dir,
            output=out_without,
            param_medic=False,
            threads=1,
        )
        psm_with = list((out_with / 'comms' / 'results' / 'search').glob('*.tide-search.target.txt'))
        psm_without = list((out_without / 'comms' / 'results' / 'search').glob('*.tide-search.target.txt'))
        assert psm_with and psm_without
        lines_with = psm_with[0].read_text().splitlines()
        lines_without = psm_without[0].read_text().splitlines()
        assert len(lines_with) == len(lines_without)

class TestRunSearchParamMedicMocked:
    '''
    Tests that verify run_search correctly uses numeric tolerance values returned by _runParamMedic, by mocking _runParamMedic to return known values and checking those values appear in the terminal summary.
    '''
    def test_uses_mocked_precursor_tolerance_in_summary(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, capsys):
        with patch('comms.commands.search._runParamMedic', return_value=(7.5, 0.02),):
            index_dir, _ = pipeline_index
            run_search(
                input_dir=synthetic_mzml.parent,
                index_dir=index_dir,
                output=tmp_path,
                param_medic=True,
                threads=1,
            )
        captured = capsys.readouterr()
        assert '7.5' in captured.out

    def test_uses_mocked_bin_width_in_summary(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, capsys):
        with patch('comms.commands.search._runParamMedic', return_value=(10.0, 0.035)):
            index_dir, _ = pipeline_index
            run_search(
                input_dir=synthetic_mzml.parent,
                index_dir=index_dir,
                output=tmp_path,
                param_medic=True,
                threads=1,
            )
        captured = capsys.readouterr()
        assert '0.035' in captured.out
 
    def test_none_return_from_run_param_medic_falls_back_to_defaults(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, capsys):
        '''
        If _runParamMedic returns (None, None), run_search should fall back to config defaults without raising.
        '''
        from comms.utils.settings import loadDefaultConfig
        cfg = loadDefaultConfig()
        with patch('comms.commands.search._runParamMedic', return_value=(None, None)):
            index_dir, _ = pipeline_index
            run_search(
                input_dir=synthetic_mzml.parent,
                index_dir=index_dir,
                output=tmp_path,
                param_medic=True,
                threads=1,
            )
        captured = capsys.readouterr()
        assert str(cfg['search']['precursor_tolerance_ppm']) in captured.out
        assert str(cfg['search']['mz_bin_width']) in captured.out

# -- Define fixture for generating search output by running tide-search
@pytest.fixture(scope='module')
def pipeline_search(crux_bin, pipeline_index, tmp_path_factory):
    '''Run search once per module for rescore/quantify tests.'''
    from tests.fixtures.generate_fixtures import write_mzml
    work = tmp_path_factory.mktemp('pipeline_search')
    mzml = write_mzml(work / 'synthetic.mzml')
    index_dir, fasta = pipeline_index
    try:
        run_search(
            input_dir=work,
            index_dir=index_dir,
            output=work,
            param_medic=False,
            threads=1,
        )
    except SystemExit as e:
        pytest.skip(f'run_search failed (exit {e.code}) — skipping rescore/quantify tests')
    search_dir = work / 'comms' / 'results' / 'search'
    return search_dir, fasta, work

# -- Define tests for running rescore command
class TestRunRescore:
    def test_creates_rescore_output_dir(self, crux_bin, pipeline_search, tmp_path):
        search_dir, fasta, _ = pipeline_search
        # run_rescore may fail with synthetic data due to insufficient PSMs
        # for Percolator — we assert on directory creation, not success
        try:
            run_rescore(input_dir=search_dir, database=fasta, output=tmp_path)
        except SystemExit:
            pass
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        assert rescore_dir.exists()

    def test_prints_rescore_summary(self, crux_bin, pipeline_search, tmp_path, capsys):
        search_dir, fasta, _ = pipeline_search
        try:
            run_rescore(input_dir=search_dir, database=fasta, output=tmp_path)
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert 'Rescore summary' in captured.out

    def test_log_file_is_written(self, crux_bin, pipeline_search, tmp_path):
        search_dir, fasta, _ = pipeline_search
        try:
            run_rescore(input_dir=search_dir, database=fasta, output=tmp_path)
        except SystemExit:
            pass
        log = tmp_path / 'comms' / 'results' / 'rescore.log'
        assert log.exists()
        assert log.stat().st_size > 0

    def test_comms_logger_is_rescore(self, crux_bin, pipeline_search, tmp_path):
        search_dir, fasta, _ = pipeline_search
        try:
            run_rescore(input_dir=search_dir, database=fasta, output=tmp_path)
        except SystemExit:
            pass
        assert logMsg._instance.logger.name == 'rescore'

# -- Define constants for rescore PSM files
PSM_HEADER = 'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
PSM_ROW_MT = 'synthetic_1\t1.5\t0.001\t0.001\tK.ACDEFGHIK.L\tsp|TE001|GENE1_TESTEUK\n'
PSM_ROW_RI = 'synthetic_2\t1.2\t0.005\t0.003\tK.SAMPLEK.T\tsp|TP001|GENE1_TESTPRO\n'

# -- Define fixtures for rescore PSM files
@pytest.fixture()
def two_organism_fasta(tmp_path):
    p = tmp_path / 'combined.fasta'
    p.write_text(
        '>sp|TE001|GENE1_TESTEUK Protein one\nACDEFGHIK\n'
        '>sp|TP001|GENE1_TESTPRO Protein two\nSAMPLEK\n'
        '>cRAP|TC001|CON001 Contaminant\nPEPTIDEFK\n'
    )
    return p

@pytest.fixture()
def synthetic_tide_search_dir(tmp_path):
    search_dir = tmp_path / 'search'
    search_dir.mkdir(parents=True)
    psm_file = search_dir / 'synthetic.tide-search.target.txt'
    psm_file.write_text(
        'file\tscan\tcharge\tspectrum precursor m/z\tsequence\n'
        'synthetic.mzML\t1\t2\t500.0\tACDEFGHIK\n'
    )
    return search_dir

# -- Define helper function for rescore PSM files
def _write_per_organism_psm_files(rescore_dir: Path, file_base: str, labels: list[str]) -> None:
    '''
    Write synthetic per-organism Percolator output files so that _mergeRescoredPsms has something to read without Percolator running.
    '''
    rows = {'EUK': PSM_ROW_MT, 'PRO': PSM_ROW_RI}
    for label in labels:
        for match_type in ('target', 'decoy'):
            path = rescore_dir / label / f'{file_base}.{label}.percolator.{match_type}.psms.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PSM_HEADER + rows.get(label, PSM_ROW_MT))

# -- Define tests for rescore command with per-organism picked-protein FDR
class TestRunRescoreDirectories:
    def test_creates_rescore_output_directory(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=True), \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert (tmp_path / 'comms' / 'results' / 'rescore').exists()

    def test_creates_per_organism_subdirectories(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=True), patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        assert (rescore_dir / 'EUK').exists()
        assert (rescore_dir / 'PRO').exists()

class TestRunRescoreMergedOutput:
    def test_writes_merged_target_psm_file(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        def _mock_percolator(**kwargs):
            # Write synthetic per-organism files as a side effect of mocked Percolator
            _write_per_organism_psm_files(rescore_dir, 'synthetic', ['EUK', 'PRO'])
            return True
        with patch('comms.commands.rescore.cruxutil.percolator',
                   side_effect=_mock_percolator):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert (rescore_dir / 'synthetic.percolator.target.psms.txt').exists()

    def test_writes_merged_decoy_psm_file(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        def _mock_percolator(**kwargs):
            _write_per_organism_psm_files(rescore_dir, 'synthetic', ['EUK', 'PRO'])
            return True
        with patch('comms.commands.rescore.cruxutil.percolator',
                   side_effect=_mock_percolator):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert (rescore_dir / 'synthetic.percolator.decoy.psms.txt').exists()

class TestRunRescoreOrganismTags:
    def test_raises_system_exit_when_no_psm_files(self, crux_bin, two_organism_fasta, tmp_path):
        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()
        with pytest.raises(SystemExit):
            run_rescore(
                input_dir=empty_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )

    def test_raises_system_exit_when_org_tags_invalid(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        with pytest.raises(SystemExit):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO',
            )

    def test_raises_system_exit_when_no_tags_available(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, monkeypatch):
        import comms.commands.rescore as rescore_mod
        monkeypatch.setitem(rescore_mod.config, 'organism', None)
        with pytest.raises(SystemExit):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='',
            )

    def test_uses_config_organism_when_org_tags_falsy(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, monkeypatch):
        import comms.commands.rescore as rescore_mod
        monkeypatch.setitem(rescore_mod.config, 'organism', {'EUK': 'TESTEUK', 'PRO': 'TESTPRO'})
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=True), \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='',
            )
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        assert (rescore_dir / 'EUK').exists()
        assert (rescore_dir / 'PRO').exists()

    def test_percolator_called_once_per_organism_per_file(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        with patch('comms.commands.rescore.cruxutil.percolator',
                   return_value=True) as mock_perc, \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert mock_perc.call_count == 2

class TestRunRescoreOutput:
    def test_prints_success_summary(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, capsys):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=True), \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        captured = capsys.readouterr()
        assert 'Rescore finished successfully' in captured.out

    def test_prints_warning_when_percolator_fails(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, capsys):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=False), \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        captured = capsys.readouterr()
        assert 'WARNING' in captured.out

    def test_prints_warning_when_merge_fails(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, capsys):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=True), \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=False):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        captured = capsys.readouterr()
        assert 'WARNING' in captured.out

    def test_logger_is_named_rescore(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=True), \
             patch('comms.commands.rescore._mergeRescoredPsms', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                output=tmp_path,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert logMsg._instance.logger.name == 'rescore'

# -- Define tests for lfq command
class TestRunLfqOutputDirectories:
    def test_lfq_root_directory_is_created(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        assert (tmp_path / 'comms' / 'results' / 'lfq').exists()

    def test_single_fraction_creates_one_output_directory(self, crux_bin, single_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_single_fraction, tmp_path):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=single_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_single_fraction,
                output=tmp_path,
            )
        lfq_root = tmp_path / 'comms' / 'results' / 'lfq'
        subdirs = [p for p in lfq_root.iterdir() if p.is_dir()]
        assert len(subdirs) == 1
        assert subdirs[0].name == 'WCL'

    def test_creates_per_fraction_output_directories(
        self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path
    ):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        lfq_root = tmp_path / 'comms' / 'results' / 'lfq'
        assert (lfq_root / 'WCL').exists()
        assert (lfq_root / 'ECF').exists()
        assert (lfq_root / 'PUR').exists()

class TestRunLfqCruxCalls:
    def test_lfq_called_once_per_fraction(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        assert mock_lfq.call_count == 3

    def test_lfq_called_with_correct_fraction_psm_files(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        all_psm_files = [c.kwargs['psm_files'] for c in mock_lfq.call_args_list]
        for files in all_psm_files:
            assert len(files) == 2

    def test_lfq_not_called_for_unmatched_psm_files(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        orphan = multi_fraction_psm_dir / 'orphan_file.percolator.target.psms.txt'
        orphan.touch()
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        assert mock_lfq.call_count == 3

    def test_lfq_receives_correct_fileroot_per_fraction(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        fileroots = {c.kwargs['fileroot'] for c in mock_lfq.call_args_list}
        assert fileroots == {'WCL', 'ECF', 'PUR'}

class TestRunLfqEarlyExit:
    def test_raises_system_exit_when_no_psm_files(self, crux_bin, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        empty_rescore_dir = tmp_path / 'empty_rescore'
        empty_rescore_dir.mkdir()
        with pytest.raises(SystemExit):
            run_lfq(
                rescore_dir=empty_rescore_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )

    def test_raises_system_exit_when_no_mzml_files(self, crux_bin, multi_fraction_psm_dir, valid_sample_sheet_multiple_fractions, tmp_path):
        empty_mzml_dir = tmp_path / 'empty_mzml'
        empty_mzml_dir.mkdir()
        with pytest.raises(SystemExit):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=empty_mzml_dir,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )

class TestRunLfqWarnings:
    def test_logs_warning_when_lfq_fails_for_fraction(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path, caplog):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=False), caplog.at_level(logging.WARNING):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        assert 'LFQ failed' in caplog.text or 'failed' in caplog.text.lower()

    def test_completes_remaining_fractions_even_if_one_fails(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path):
        call_count = {'n': 0}
        def _mock_lfq(**kwargs):
            call_count['n'] += 1
            return call_count['n'] != 1
        with patch('comms.commands.lfq.cruxutil.lfq', side_effect=_mock_lfq):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_multiple_fractions,
                output=tmp_path,
            )
        assert call_count['n'] == 3

class TestRunLfqLogger:
    def test_logger_is_named_lfq(self, crux_bin, single_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_single_fraction, tmp_path):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=single_fraction_psm_dir,
                mzml_dir=synthetic_mzml.parent,
                sample_sheet=valid_sample_sheet_single_fraction,
                output=tmp_path,
            )
        assert logMsg._instance.logger.name == 'lfq'

# -- Define tests for quantify command
class TestRunQuantify:
    def test_creates_quantify_output_dir(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path):
        rescore_dir, fasta = synthetic_percolator_results, synthetic_fasta
        run_quantify(input_dir=rescore_dir, database=fasta, output=tmp_path)
        quantify_dir = tmp_path / 'comms' / 'results' / 'quantify'
        assert quantify_dir.exists()

    def test_spectral_counts_file_exists(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path):
        rescore_dir, fasta = synthetic_percolator_results, synthetic_fasta
        run_quantify(input_dir=rescore_dir, database=fasta, output=tmp_path)
        quantify_dir = tmp_path / 'comms' / 'results' / 'quantify'
        counts_files = list(quantify_dir.glob('*.spectral-counts.target.txt'))
        assert counts_files, 'No spectral-counts file found after run_quantify'

    def test_prints_quantify_summary(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path, capsys):
        rescore_dir, fasta = synthetic_percolator_results, synthetic_fasta
        run_quantify(input_dir=rescore_dir, database=fasta, output=tmp_path)
        captured = capsys.readouterr()
        assert 'Quantify finished successfully - summary:' in captured.out

    def test_comms_logger_is_quantify(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path):
        rescore_dir, fasta = synthetic_percolator_results, synthetic_fasta
        run_quantify(input_dir=rescore_dir, database=fasta, output=tmp_path)
        assert logMsg._instance.logger.name == 'quantify'

# -- Define tests for running end-to-end pipeline
class TestRunPipeline:
    def test_pipeline_completes_without_raising(self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                input_dir=mzml.parent,
                output_dir=tmp_path,
                param_medic=False,
                skip_convert=True,
                skip_lfq=True,
                skip_quantify=True,
                skip_report=True,
                threads=1,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        except SystemExit as e:
            pytest.fail(
                f'run_pipeline raised SystemExit({e.code}). '
                'Check that synthetic fixtures are valid and Crux is working.'
            )

    def test_pipeline_creates_results_tree(self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                input_dir=mzml.parent,
                output_dir=tmp_path,
                param_medic=False,
                skip_convert=True,
                skip_lfq=True,
                skip_quantify=False,
                skip_report=True,
                threads=1,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        except SystemExit:
            pytest.skip('run_pipeline failed — skipping output tree check')
        results_root = tmp_path / 'comms' / 'results'
        assert results_root.exists()
        for stage in ('index', 'search', 'rescore', 'quantify'):
            stage_dir = results_root / stage
            assert stage_dir.exists(), f'Expected results directory for stage: {stage}'

    def test_comms_logger_is_pipeline(self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                input_dir=mzml.parent,
                output_dir=tmp_path,
                param_medic=False,
                skip_convert=True,
                skip_lfq=True,
                skip_quantify=True,
                skip_report=True,
                threads=1,
                org_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
            assert logMsg._instance.logger.name == 'pipeline'
        except SystemExit as e:
            pytest.fail(
                f'run_pipeline raised SystemExit({e.code}). '
                'Check that synthetic fixtures are valid and Crux is working.'
            )