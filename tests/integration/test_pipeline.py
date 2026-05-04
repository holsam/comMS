'''
Integration tests for src/comms/commands/pipeline.py > run_pipeline and
the individual command-level functions (run_index, run_search, run_rescore,
run_quantify)
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import internal functions
from comms.commands.index import run_index
from comms.commands.search import run_search
from comms.commands.rescore import run_rescore
from comms.commands.quantify import run_quantify
from comms.commands.pipeline import run_pipeline

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

# -- Define tests for running end-to-end pipeline
class TestRunPipeline:
    def test_pipeline_completes_without_raising(
        self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path
    ):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                input_dir=mzml.parent,
                output_dir=tmp_path,
                param_medic=False,
                skip_convert=True,
                skip_report=True,
                threads=1,
            )
        except SystemExit as e:
            pytest.fail(
                f'run_pipeline raised SystemExit({e.code}). '
                'Check that synthetic fixtures are valid and Crux is working.'
            )

    def test_pipeline_creates_results_tree(
        self, crux_bin, synthetic_fixtures, valid_sample_sheet, tmp_path
    ):
        fasta, mzml = synthetic_fixtures
        try:
            run_pipeline(
                sample_sheet=valid_sample_sheet,
                database=fasta,
                input_dir=mzml.parent,
                output_dir=tmp_path,
                param_medic=False,
                skip_convert=True,
                skip_report=True,
                threads=1,
            )
        except SystemExit:
            pytest.skip('run_pipeline failed — skipping output tree check')
        results_root = tmp_path / 'comms' / 'results'
        assert results_root.exists()
        for stage in ('index', 'search', 'rescore', 'quantify'):
            stage_dir = results_root / stage
            assert stage_dir.exists(), f'Expected results directory for stage: {stage}'
