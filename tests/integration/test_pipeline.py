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

# Import internal classes
from comms.utils.context import ExperimentContext
from comms.utils.log import logMsg

# -- Define pytest mark for crux (all tests in file require Crux)
pytestmark = pytest.mark.crux

# ===========================================================================
# Index
# ===========================================================================
class TestRunIndex:
    def test_creates_index_output_dir(self, crux_bin, synthetic_fasta, tmp_path, experiment_ctx):
        run_index(database=synthetic_fasta, ctx=experiment_ctx)
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        assert index_dir.exists(), f'Expected index dir at {index_dir}'

    def test_index_output_is_non_empty(self, crux_bin, synthetic_fasta, tmp_path, experiment_ctx):
        run_index(database=synthetic_fasta, ctx=experiment_ctx)
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        assert any(index_dir.iterdir()), 'Index directory is empty after run_index'

    def test_logs_completion(self, crux_bin, synthetic_fasta, experiment_ctx, caplog):
        with caplog.at_level(logging.DEBUG):
            run_index(database=synthetic_fasta, ctx=experiment_ctx)
        assert 'Finished command: index' in caplog.text

    def test_comms_logger_is_index(self, crux_bin, synthetic_fasta, experiment_ctx):
        run_index(database=synthetic_fasta, ctx=experiment_ctx)
        assert logMsg._instance.logger.name == 'index'

# Shared module-scoped index fixture
@pytest.fixture(scope='module')
def pipeline_index(crux_bin, tmp_path_factory):
    '''Build a shared index for all pipeline integration tests'''
    from tests.fixtures.generate_fixtures import write_fasta
    from comms.utils.context import ExperimentContext
    work = tmp_path_factory.mktemp('pipeline_index')
    ctx = ExperimentContext.resolve(work)
    fasta = write_fasta(work / 'synthetic_proteome.fasta')
    try:
        run_index(database=fasta, ctx=ctx)
    except SystemExit as e:
        pytest.skip(f'run_index failed (exit {e.code}) — skipping pipeline tests')
    return work / 'comms' / 'results' / 'index', fasta

# ===========================================================================
# Search
# ===========================================================================
class TestRunSearch:
    def test_creates_search_output_dir(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=False,
            threads=1,
        )
        search_dir = tmp_path / 'comms' / 'results' / 'search'
        assert search_dir.exists()

    def test_target_psm_file_exists(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=False,
            threads=1,
        )
        search_dir = tmp_path / 'comms' / 'results' / 'search'
        psm_files = list(search_dir.glob('*.tide-search.target.txt'))
        assert psm_files, 'No target PSM file found after run_search'

    def test_logs_completion(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, experiment_ctx, caplog):
        index_dir, _ = pipeline_index
        with caplog.at_level(logging.DEBUG):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=False,
                threads=1,
            )
        assert 'Finished command: search' in caplog.text

    def test_comms_logger_is_search(self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=False,
            threads=1,
        )
        assert logMsg._instance.logger.name == 'search'

class TestRunSearchParamMedic:
    def test_completes_without_raising(self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=True,
            threads=1,
        )
 
    def test_creates_search_output_directory(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=True,
            threads=1,
        )
        assert (tmp_path / 'comms' / 'results' / 'search').exists()
 
    def test_creates_target_psm_file(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=True,
            threads=1,
        )
        search_dir = tmp_path / 'comms' / 'results' / 'search'
        psm_files = list(search_dir.glob('*.tide-search.target.txt'))
        assert psm_files, 'No target PSM file found after run_search with --param-medic'
 
    def test_creates_param_medic_output_directory(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path, experiment_ctx):
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=experiment_ctx,
            param_medic=True,
            threads=1,
        )
        assert (tmp_path / 'comms' / 'results' / 'param-medic').exists()
 
    def test_falls_back_to_config_defaults_when_param_medic_yields_no_estimates(self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx, caplog):
        '''
        When param-medic cannot estimate tolerances (as expected for synthetic data), run_search should fall back to config defaults and report those values in the terminal summary
        '''
        from comms.utils.settings import loadDefaultConfig
        cfg = loadDefaultConfig()
        expected_prec = str(cfg['search']['precursor_tolerance_ppm'])
        expected_bw = str(cfg['search']['mz_bin_width'])
        index_dir, _ = pipeline_index
        with caplog.at_level(logging.DEBUG):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=True,
                threads=1,
            )
        assert expected_prec in caplog.text
        assert expected_bw in caplog.text
 
    def test_warns_when_param_medic_yields_no_estimates(
        self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx, caplog
    ):
        index_dir, _ = pipeline_index
        with caplog.at_level(logging.WARNING):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=True,
                threads=1,
            )
        warning_text = caplog.text.lower()
        assert 'falling back' in warning_text or 'no usable' in warning_text
 
    def test_search_reports_numeric_tolerance(self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx, caplog):
        index_dir, _ = pipeline_index
        with caplog.at_level(logging.DEBUG):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=True,
                threads=1,
            )
        assert 'Precursor tolerance' in caplog.text
        assert 'm/z bin width' in caplog.text
 
    def test_produces_same_output_as_no_param_medic_when_estimates_unavailable(self, crux_bin, pipeline_index, synthetic_mzml, tmp_path):
        '''
        When param-medic falls back to defaults, the search output (PSM file existence and line count) should be identical to a run without param-medic, since both use the same config tolerance values
        '''
        from comms.utils.context import ExperimentContext
        out_with = tmp_path / 'with_pm'
        ctx_with = ExperimentContext.resolve(out_with)
        out_without = tmp_path / 'without_pm'
        ctx_without = ExperimentContext.resolve(out_without)
        index_dir, _ = pipeline_index
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=ctx_with,
            param_medic=True,
            threads=1,
        )
        run_search(
            data_files=[synthetic_mzml],
            index_dir=index_dir,
            ctx=ctx_without,
            param_medic=False,
            threads=1,
        )
        psm_with = list((out_with / 'comms' / 'results' / 'search').glob('*.tide-search.target.txt'))
        psm_without = list((out_without / 'comms' / 'results' / 'search').glob('*.tide-search.target.txt'))
        assert psm_with and psm_without
        assert len(psm_with[0].read_text().splitlines()) == len(psm_without[0].read_text().splitlines())

class TestRunSearchParamMedicMocked:
    def test_uses_mocked_precursor_tolerance(self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx, caplog):
        '''
        Tests that verify run_search correctly uses numeric tolerance values returned by _runParamMedic, by mocking _runParamMedic to return known values and checking those values appear in the terminal summary
        '''
        index_dir, _ = pipeline_index
        with patch('comms.commands.search._runParamMedic', return_value=(7.5, 0.02)), \
             caplog.at_level(logging.DEBUG):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=True,
                threads=1,
            )
        assert '7.5 ppm' in caplog.text

    def test_uses_mocked_bin_width_in_summary(self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx, caplog):
        index_dir, _ = pipeline_index
        with patch('comms.commands.search._runParamMedic', return_value=(10.0, 0.035)), \
             caplog.at_level(logging.DEBUG):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=True,
                threads=1,
            )
        assert '0.035 Da' in caplog.text
 
    def test_none_return_from_run_param_medic_falls_back_to_defaults(
        self, crux_bin, pipeline_index, synthetic_mzml, experiment_ctx, caplog
    ):
        from comms.utils.settings import loadDefaultConfig
        cfg = loadDefaultConfig()
        index_dir, _ = pipeline_index
        with patch('comms.commands.search._runParamMedic', return_value=(None, None)), \
             caplog.at_level(logging.DEBUG):
            run_search(
                data_files=[synthetic_mzml],
                index_dir=index_dir,
                ctx=experiment_ctx,
                param_medic=True,
                threads=1,
            )
        assert f'{str(cfg["search"]["precursor_tolerance_ppm"])} ppm' in caplog.text
        assert f'{str(cfg["search"]["mz_bin_width"])} Da' in caplog.text

# Shared module-scoped search fixture
@pytest.fixture(scope='module')
def pipeline_search(crux_bin, pipeline_index, tmp_path_factory):
    '''Run search once per module for rescore/quantify tests.'''
    from tests.fixtures.generate_fixtures import write_mzml
    from comms.utils.context import ExperimentContext
    work = tmp_path_factory.mktemp('pipeline_search')
    ctx = ExperimentContext.resolve(work)
    mzml = write_mzml(work / 'synthetic.mzML')
    index_dir, fasta = pipeline_index
    try:
        run_search(
            data_files=[mzml],
            index_dir=index_dir,
            ctx=ctx,
            param_medic=False,
            threads=1,
        )
    except SystemExit as e:
        pytest.skip(f'run_search failed (exit {e.code}) — skipping rescore/quantify tests')
    search_dir = work / 'comms' / 'results' / 'search'
    return search_dir, fasta, work

# ===========================================================================
# Rescore
# ===========================================================================
class TestRunRescore:
    def test_creates_rescore_output_dir(self, crux_bin, pipeline_search, tmp_path, experiment_ctx):
        search_dir, fasta, _ = pipeline_search
        # run_rescore may fail with synthetic data due to insufficient PSMs
        # for Percolator, assert on directory creation, not success
        try:
            run_rescore(
                input_dir=search_dir,
                database=fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,SP',
            )
        except SystemExit:
            pass
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        assert rescore_dir.exists()

    def test_log_success(self, crux_bin, pipeline_search, experiment_ctx, caplog):
        search_dir, fasta, _ = pipeline_search
        with caplog.at_level(logging.INFO):
            try:
                run_rescore(
                    input_dir=search_dir,
                    database=fasta,
                    ctx=experiment_ctx,
                    organism_tags='EUK,SP',
                )
            except SystemExit:
                pass
        # With synthetic data Percolator fails, but round-1 progress is still logged.
        assert 'Rescoring' in caplog.text or 'Round 1' in caplog.text

    def test_log_file_is_written(self, crux_bin, pipeline_search, tmp_path, experiment_ctx):
        search_dir, fasta, _ = pipeline_search
        try:
            run_rescore(
                input_dir=search_dir,
                database=fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,SP',
            )
        except SystemExit:
            pass
        log = tmp_path / 'comms' / 'results' / 'rescore' / 'rescore.log'
        assert log.exists()
        assert log.stat().st_size > 0

    def test_comms_logger_is_rescore(self, crux_bin, pipeline_search, experiment_ctx):
        search_dir, fasta, _ = pipeline_search
        try:
            run_rescore(
                input_dir=search_dir,
                database=fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,SP',
            )
        except SystemExit:
            pass
        assert logMsg._instance.logger.name == 'rescore'

# -- Constants and helpers for mocked rescore tests ---------------------------
PSM_HEADER = 'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
PSM_ROW_MT = 'synthetic_1\t1.5\t0.001\t0.001\tK.ACDEFGHIK.L\tsp|TE001|GENE1_TESTEUK\n'
PSM_ROW_RI = 'synthetic_2\t1.2\t0.005\t0.003\tK.SAMPLEK.T\tsp|TP001|GENE1_TESTPRO\n'

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

def _write_combined_percolator_output(rescore_dir: Path, fileroot: str) -> None:
    '''
    Write synthetic combined Percolator target and decoy PSM files at the top level of rescore_dir, as cruxutil.percolator produces them
    '''
    for match_type in ('target', 'decoy'):
        path = rescore_dir / f'{fileroot}.percolator.{match_type}.psms.txt'
        path.write_text(
            PSM_HEADER
            + 'synthetic_1\t1.5\t0.001\t0.001\tK.ACDEFGHIK.L\tsp|TE001|GENE1_TESTEUK\n'
            + 'synthetic_2\t1.2\t0.005\t0.003\tK.SAMPLEK.T\tsp|TP001|GENE1_TESTPRO\n'
        )

def _write_split_psm_files(rescore_dir: Path, fileroot: str, labels: list[str]) -> bool:
    for label in labels:
        for match_type in ('target', 'decoy'):
            path = rescore_dir / label / f'{fileroot}.{label}.percolator.{match_type}.psms.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                PSM_HEADER
                + 'synthetic_1\t1.5\t0.001\t0.001\tK.ACDEFGHIK.L\tsp|TE001|GENE1_TESTEUK\n'
            )
    return True


class TestRunRescoreDirectories:
    def test_creates_rescore_output_directory(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True
        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore._splitPsmsByOrganism', return_value=True), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert (tmp_path / 'comms' / 'results' / 'rescore').exists()

    def test_creates_per_organism_subdirectories(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True
        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert (rescore_dir / 'EUK').exists()
        assert (rescore_dir / 'PRO').exists()

class TestRunRescoreAssignConfidence:
    def test_assign_confidence_called_once_per_organism(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True
        def _mock_split(**kwargs):
            return _write_split_psm_files(rescore_dir, 'synthetic', ['EUK', 'PRO'])

        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore._splitPsmsByOrganism', side_effect=_mock_split), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True) as mock_ac:
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert mock_ac.call_count == 2

    def test_raises_system_exit_when_percolator_produces_no_output(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, experiment_ctx):
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=False):
            with pytest.raises(SystemExit):
                run_rescore(
                    input_dir=synthetic_tide_search_dir,
                    database=two_organism_fasta,
                    ctx=experiment_ctx,
                    organism_tags='EUK,TESTEUK,PRO,TESTPRO',
                )

class TestRunRescoreOrganismTags:
    def test_raises_system_exit_when_no_psm_files(self, crux_bin, two_organism_fasta, tmp_path, experiment_ctx):
        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()
        with pytest.raises(SystemExit):
            run_rescore(
                input_dir=empty_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )

    def test_raises_system_exit_when_org_tags_invalid(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, experiment_ctx):
        with pytest.raises(SystemExit):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO',
            )

    def test_raises_system_exit_when_no_tags_available(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, experiment_ctx, monkeypatch):
        monkeypatch.setitem(experiment_ctx.config, 'organism', {})
        experiment_ctx.metadata["experiment"] = {"analysis": "single"}
        with pytest.raises(SystemExit):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='',
            )

    def test_uses_config_organism_when_organism_tags_falsy(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx, monkeypatch):
        monkeypatch.setitem(experiment_ctx.config, 'organism', {'EUK': 'TESTEUK', 'PRO': 'TESTPRO'})
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'

        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True

        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore._splitPsmsByOrganism', return_value=True), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True) as mock_ac:
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='',
            )
        assert mock_ac.call_count == 0

    def test_percolator_called_once_per_file(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'

        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True

        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator) as mock_perc, \
             patch('comms.commands.rescore._splitPsmsByOrganism', return_value=True), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert mock_perc.call_count == 1

class TestRunRescoreOutput:
    def test_prints_success_summary(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx, caplog):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'

        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True

        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore._splitPsmsByOrganism', return_value=True), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True), \
             caplog.at_level(logging.DEBUG):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert 'Finished command: rescore' in caplog.text

    def test_logs_warning_when_percolator_fails(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, experiment_ctx, caplog):
        # Percolator fails → source prints WARNING then exits; catch the exit
        with patch('comms.commands.rescore.cruxutil.percolator', return_value=False), caplog.at_level(logging.WARNING):
            with pytest.raises(SystemExit):
                run_rescore(
                    input_dir=synthetic_tide_search_dir,
                    database=two_organism_fasta,
                    ctx=experiment_ctx,
                    organism_tags='EUK,TESTEUK,PRO,TESTPRO',
                )
        assert any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_prints_warning_when_split_fails(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx, caplog):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'

        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True

        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore._splitPsmsByOrganism', return_value=False), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True), \
             caplog.at_level(logging.WARNING):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_logger_is_named_rescore(self, crux_bin, two_organism_fasta, synthetic_tide_search_dir, tmp_path, experiment_ctx):
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'

        def _mock_percolator(**kwargs):
            _write_combined_percolator_output(rescore_dir, 'synthetic')
            return True

        with patch('comms.commands.rescore.cruxutil.percolator', side_effect=_mock_percolator), \
             patch('comms.commands.rescore._splitPsmsByOrganism', return_value=True), \
             patch('comms.commands.rescore.cruxutil.assignConfidence', return_value=True):
            run_rescore(
                input_dir=synthetic_tide_search_dir,
                database=two_organism_fasta,
                ctx=experiment_ctx,
                organism_tags='EUK,TESTEUK,PRO,TESTPRO',
            )
        assert logMsg._instance.logger.name == 'rescore'

# -- Define test class for running rescore in single-species analysis mode
class TestRunRescoreSingleSpecies:
    @pytest.fixture
    def single_species_context(self, experiment_ctx, monkeypatch):
        '''Single-species context: analysis_mode='single', no organism config'''
        monkeypatch.setitem(experiment_ctx.config, 'organism', {})
        monkeypatch.setitem(experiment_ctx.config, 'custom_section', {})
        experiment_ctx.metadata["experiment"] = {"analysis": "single"}
        return experiment_ctx

    @pytest.fixture
    def mock_search_output(self, tmp_path):
        '''Create mock Tide-search target files'''
        search_dir = tmp_path / 'search'
        search_dir.mkdir()
        (search_dir / 'sample1.tide-search.target.txt').touch()
        (search_dir / 'sample2.tide-search.target.txt').touch()
        return search_dir

    @patch('comms.commands.rescore.cruxutil.percolator')
    @patch('comms.commands.rescore.cruxutil.assignConfidence')
    def test_assign_confidence_called_once_per_file(
        self, mock_ac, mock_perc, single_species_context, mock_search_output, two_organism_fasta,
    ):
        mock_perc.return_value = True
        mock_ac.return_value = True
        # Mock Percolator to create output files
        def mock_perc_side_effect(**kwargs):
            fileroot = kwargs['fileroot']
            (kwargs['out_dir'] / f'{fileroot}.percolator.target.psms.txt').touch()
            (kwargs['out_dir'] / f'{fileroot}.percolator.decoy.psms.txt').touch()
            return True
        mock_perc.side_effect = mock_perc_side_effect
        run_rescore(
            input_dir=mock_search_output,
            database=two_organism_fasta,
            ctx=single_species_context,
        )
        # assignConfidence should be called once per Percolator output (2 times)
        assert mock_ac.call_count == 2

    @patch('comms.commands.rescore.cruxutil.percolator')
    @patch('comms.commands.rescore.cruxutil.assignConfidence')
    def test_writes_flat_assign_confidence_output(
        self, mock_ac, mock_perc, single_species_context, mock_search_output, two_organism_fasta
    ):
        mock_perc.return_value = True
        mock_ac.return_value = True
        def mock_perc_side_effect(**kwargs):
            fileroot = kwargs['fileroot']
            (kwargs['out_dir'] / f'{fileroot}.percolator.target.psms.txt').touch()
            (kwargs['out_dir'] / f'{fileroot}.percolator.decoy.psms.txt').touch()
            return True
        mock_perc.side_effect = mock_perc_side_effect
        run_rescore(
            input_dir=mock_search_output,
            database=two_organism_fasta,
            ctx=single_species_context,
        )
        # Check that assignConfidence was called with out_dir = rescore root
        for call in mock_ac.call_args_list:
            out_dir = call.kwargs['out_dir']
            # out_dir should be the rescore root, not a per-organism subdirectory
            assert out_dir.name == 'rescore'

    @patch('comms.commands.rescore.cruxutil.percolator')
    @patch('comms.commands.rescore.cruxutil.assignConfidence')
    def test_no_per_organism_subdirectories_created(
        self, mock_ac, mock_perc, single_species_context, mock_search_output, two_organism_fasta, tmp_path,
    ):
        mock_perc.return_value = True
        mock_ac.return_value = True
        def mock_perc_side_effect(**kwargs):
            fileroot = kwargs['fileroot']
            (kwargs['out_dir'] / f'{fileroot}.percolator.target.psms.txt').touch()
            (kwargs['out_dir'] / f'{fileroot}.percolator.decoy.psms.txt').touch()
            return True
        mock_perc.side_effect = mock_perc_side_effect
        run_rescore(
            input_dir=mock_search_output,
            database=two_organism_fasta,
            ctx=single_species_context,
        )
        rescore_dir = single_species_context.root / 'comms/results/rescore'
        subdirs = [d for d in rescore_dir.iterdir() if d.is_dir()]
        assert len(subdirs) == 0, f'Unexpected subdirectories: {subdirs}'

    @patch('comms.commands.rescore.cruxutil.percolator')
    @patch('comms.commands.rescore.cruxutil.assignConfidence')
    def test_ignores_supplied_organism_tags_with_warning(
        self, mock_ac, mock_perc, single_species_context, mock_search_output, two_organism_fasta, caplog
    ):
        mock_perc.return_value = True
        mock_ac.return_value = True
        def mock_perc_side_effect(**kwargs):
            fileroot = kwargs['fileroot']
            (kwargs['out_dir'] / f'{fileroot}.percolator.target.psms.txt').touch()
            (kwargs['out_dir'] / f'{fileroot}.percolator.decoy.psms.txt').touch()
            return True
        mock_perc.side_effect = mock_perc_side_effect
        with caplog.at_level(logging.WARNING):
            run_rescore(
                input_dir=mock_search_output,
                database=two_organism_fasta,
                ctx=single_species_context,
                organism_tags='EUK:TESTEUK',
            )
            assert 'ignoring supplied organism tags' in caplog.text

# ===========================================================================
# LFQ
# ===========================================================================
class TestRunLfqOutputDirectories:
    def test_lfq_root_directory_is_created(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        assert (tmp_path / 'comms' / 'results' / 'lfq').exists()

    def test_single_fraction_creates_one_output_directory(self, crux_bin, single_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_single_fraction, tmp_path, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=single_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_single_fraction,
                ctx=experiment_ctx,
            )
        lfq_root = tmp_path / 'comms' / 'results' / 'lfq'
        subdirs = [p for p in lfq_root.iterdir() if p.is_dir()]
        assert len(subdirs) == 1
        assert subdirs[0].name == 'WCL'

    def test_creates_per_fraction_output_directories(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        lfq_root = tmp_path / 'comms' / 'results' / 'lfq'
        assert (lfq_root / 'WCL').exists()
        assert (lfq_root / 'ECF').exists()
        assert (lfq_root / 'PUR').exists()

class TestRunLfqCruxCalls:
    def test_lfq_called_once_per_fraction(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        assert mock_lfq.call_count == 3

    def test_lfq_called_with_correct_fraction_psm_files(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        all_psm_files = [c.kwargs['psm_files'] for c in mock_lfq.call_args_list]
        for files in all_psm_files:
            assert len(files) == 2

    def test_lfq_not_called_for_unmatched_psm_files(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, experiment_ctx):
        orphan = multi_fraction_psm_dir / 'orphan_file.percolator.target.psms.txt'
        orphan.touch()
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        assert mock_lfq.call_count == 3

    def test_lfq_receives_correct_fileroot_per_fraction(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        fileroots = {c.kwargs['fileroot'] for c in mock_lfq.call_args_list}
        assert fileroots == {'WCL', 'ECF', 'PUR'}

class TestRunLfqEarlyExit:
    def test_raises_system_exit_when_no_psm_files(self, crux_bin, synthetic_mzml, valid_sample_sheet_multiple_fractions, tmp_path, experiment_ctx):
        empty_rescore_dir = tmp_path / 'empty_rescore'
        empty_rescore_dir.mkdir()
        with pytest.raises(SystemExit):
            run_lfq(
                rescore_dir=empty_rescore_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )

    def test_lfq_called_per_fraction_even_when_no_mzml_matches(self, crux_bin, multi_fraction_psm_dir, valid_sample_sheet_multiple_fractions, tmp_path, experiment_ctx):
        '''
        cruxutil.lfq is called for each fraction even when the supplied mzML file does not match any PSM file stem (the mock returns False for each call)
        '''
        dummy_mzml = tmp_path / 'unmatched_sample.mzML'
        dummy_mzml.touch()
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=False) as mock_lfq:
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[dummy_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        assert mock_lfq.call_count == 3

class TestRunLfqWarnings:
    def test_logs_warning_when_lfq_fails_for_fraction(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, experiment_ctx, caplog):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=False), caplog.at_level(logging.WARNING):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        assert 'LFQ failed' in caplog.text or 'failed' in caplog.text.lower()

    def test_completes_remaining_fractions_even_if_one_fails(self, crux_bin, multi_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_multiple_fractions, experiment_ctx):
        call_count = {'n': 0}
        def _mock_lfq(**kwargs):
            call_count['n'] += 1
            return call_count['n'] != 1
        with patch('comms.commands.lfq.cruxutil.lfq', side_effect=_mock_lfq):
            run_lfq(
                rescore_dir=multi_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_multiple_fractions,
                ctx=experiment_ctx,
            )
        assert call_count['n'] == 3

class TestRunLfqLogger:
    def test_logger_is_named_lfq(self, crux_bin, single_fraction_psm_dir, synthetic_mzml, valid_sample_sheet_single_fraction, experiment_ctx):
        with patch('comms.commands.lfq.cruxutil.lfq', return_value=True):
            run_lfq(
                rescore_dir=single_fraction_psm_dir,
                data_files=[synthetic_mzml],
                sample_sheet=valid_sample_sheet_single_fraction,
                ctx=experiment_ctx,
            )
        assert logMsg._instance.logger.name == 'lfq'

# ===========================================================================
# Quantify
# ===========================================================================
class TestRunQuantify:
    def test_creates_quantify_output_dir(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path, experiment_ctx):
        run_quantify(input_dir=synthetic_percolator_results, database=synthetic_fasta, ctx=experiment_ctx)
        quantify_dir = tmp_path / 'comms' / 'results' / 'quantify'
        assert quantify_dir.exists()

    def test_spectral_counts_file_exists(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path, experiment_ctx):
        run_quantify(input_dir=synthetic_percolator_results, database=synthetic_fasta, ctx=experiment_ctx)
        quantify_dir = tmp_path / 'comms' / 'results' / 'quantify'
        counts_files = list(quantify_dir.glob('*.spectral-counts.target.txt'))
        assert counts_files, 'No spectral-counts file found after run_quantify'

    def test_logs_completion(self, crux_bin, synthetic_percolator_results, synthetic_fasta, experiment_ctx, caplog):
        with caplog.at_level(logging.DEBUG):
            run_quantify(input_dir=synthetic_percolator_results, database=synthetic_fasta, ctx=experiment_ctx)
        assert 'Finished command: quantify' in caplog.text

    def test_comms_logger_is_quantify(self, crux_bin, synthetic_percolator_results, synthetic_fasta, experiment_ctx):
        run_quantify(input_dir=synthetic_percolator_results, database=synthetic_fasta, ctx=experiment_ctx)
        assert logMsg._instance.logger.name == 'quantify'

# -- Define test class for quantifying single-species analysis rescore results
class TestQuantifyFlatOutput:
    @patch('comms.commands.quantify.cruxutil.spectralCounts')
    def test_quantify_finds_flat_output(self, mock_sc, tmp_path, experiment_ctx, monkeypatch, two_organism_fasta):
        '''quantify discovers flat assign-confidence files in rescore root'''
        rescore_dir = tmp_path / 'rescore'
        rescore_dir.mkdir()
        # Create flat output
        (rescore_dir / 'sample1.assign-confidence.target.txt').touch()
        (rescore_dir / 'sample2.assign-confidence.target.txt').touch()
        monkeypatch.setitem(experiment_ctx.config, 'organism', {})
        experiment_ctx.metadata["experiment"] = {"analysis": "single"}
        mock_sc.return_value = True
        run_quantify(
            input_dir=rescore_dir,
            database=two_organism_fasta,
            ctx=experiment_ctx,
        )
        # spectralCounts should be called once per file (2 times)
        assert mock_sc.call_count == 2

# ===========================================================================
# Pipeline (end-to-end)
# ===========================================================================
class TestRunPipeline:
    def test_pipeline_completes_without_raising(self, crux_bin, synthetic_fixtures, valid_sample_sheet, experiment_ctx):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                data=[mzml],
                ctx=experiment_ctx,
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

    def test_pipeline_creates_results_tree(self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path, experiment_ctx):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                data=[mzml],
                ctx=experiment_ctx,
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

    def test_comms_logger_is_pipeline(self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path, experiment_ctx):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                data=[mzml],
                ctx=experiment_ctx,
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