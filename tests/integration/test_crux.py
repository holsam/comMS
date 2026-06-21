'''
Integration tests for src/comms/utils/crux.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import internal functions
from comms.utils.crux import findCrux, tideIndex, tideSearch, percolator, spectralCounts, paramMedic
from comms.utils.settings import loadDefaultConfig

# -- Define pytest mark for crux (all tests in file require Crux)
pytestmark = pytest.mark.crux

# -- Define tests for locating Crux binary
class TestFindCrux:
    def test_returns_path_to_existing_binary(self, crux_bin):
        assert crux_bin.exists()

    def test_returned_path_is_executable(self, crux_bin):
        import os
        assert os.access(crux_bin, os.X_OK)

    def test_returns_none_for_empty_bin_dir(self, tmp_path):
        result = findCrux(tmp_path)
        assert result is None

# -- Define tests for running tide-index Crux command
class TestTideIndex:
    def test_creates_index_directory(self, crux_bin, synthetic_fasta, tmp_path):
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        cfg = loadDefaultConfig()
        ok = tideIndex(crux_bin, synthetic_fasta, index_dir, cfg)
        assert ok, 'tideIndex returned False — check index.log for details'
        assert index_dir.exists()

    def test_index_directory_is_non_empty(self, crux_bin, synthetic_fasta, tmp_path):
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        cfg = loadDefaultConfig()
        tideIndex(crux_bin, synthetic_fasta, index_dir, cfg)
        assert any(index_dir.iterdir()), 'Index directory is empty after tideIndex'

    def test_log_file_is_written(self, crux_bin, synthetic_fasta, tmp_path):
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        log = index_dir / 'tide-index.log.txt'
        cfg = loadDefaultConfig()
        tideIndex(crux_bin, synthetic_fasta, index_dir, cfg)
        assert log.exists()
        assert log.stat().st_size > 0

    def test_returns_false_on_bad_fasta(self, crux_bin, tmp_path):
        bad_fasta = tmp_path / 'bad.fasta'
        bad_fasta.write_text('NOT A FASTA FILE\n')
        index_dir = tmp_path / 'comms' / 'results' / 'index'
        cfg = loadDefaultConfig()
        ok = tideIndex(crux_bin, bad_fasta, index_dir, cfg)
        # Crux should exit non-zero
        assert not ok or not any(index_dir.iterdir()) if index_dir.exists() else True

# -- Define fixture for generating index using tide-index
@pytest.fixture(scope='module')
def built_index(crux_bin, tmp_path_factory):
    '''Build a Tide index once per module and share it across search tests.'''
    from tests.fixtures.generate_fixtures import write_fasta
    work = tmp_path_factory.mktemp('crux_index_module')
    fasta = write_fasta(work / 'synthetic_proteome.fasta')
    index_dir = work / 'comms' / 'results' / 'index'
    cfg = loadDefaultConfig()
    ok = tideIndex(crux_bin, fasta, index_dir, cfg)
    if not ok:
        pytest.skip('tideIndex failed — cannot run search tests')
    return index_dir

# -- Define tests for running tide-search Crux command
class TestTideSearch:
    def test_creates_target_psm_file(self, crux_bin, built_index, synthetic_mzml, tmp_path):
        cfg = loadDefaultConfig()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        ok = tideSearch(
            crux_bin=crux_bin,
            mzml_file=synthetic_mzml,
            index_dir=built_index,
            out_dir=out_dir,
            fileroot='synthetic',
            config=cfg,
            threads=cfg['search']['threads']
        )
        assert ok, 'tideSearch returned False — check search.log'
        target_file = out_dir / 'synthetic.tide-search.target.txt'
        assert target_file.exists(), f'Expected {target_file} to exist'

    def test_target_file_has_header_and_data(self, crux_bin, built_index, synthetic_mzml, tmp_path):
        cfg = loadDefaultConfig()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        tideSearch(
            crux_bin=crux_bin,
            mzml_file=synthetic_mzml,
            index_dir=built_index,
            out_dir=out_dir,
            fileroot='synthetic',
            config=cfg,
            threads=cfg['search']['threads']
        )
        target_file = out_dir / 'synthetic.tide-search.target.txt'
        lines = target_file.read_text().splitlines()
        assert len(lines) >= 2, 'Target PSM file should have at least a header and one data row'

    def test_log_file_is_written(self, crux_bin, built_index, synthetic_mzml, tmp_path):
        cfg = loadDefaultConfig()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        tideSearch(
            crux_bin=crux_bin,
            mzml_file=synthetic_mzml,
            index_dir=built_index,
            out_dir=out_dir,
            fileroot='synthetic',
            config=cfg,
            threads=cfg['search']['threads']
        )
        log = out_dir / 'synthetic.tide-search.log.txt'
        assert log.exists()

# -- Define fixture for generating search results using tide-search
@pytest.fixture(scope='module')
def search_results(crux_bin, built_index, tmp_path_factory):
    '''Run tideSearch once per module and return (out_dir, target_file, fasta).'''
    from tests.fixtures.generate_fixtures import write_fasta, write_mzml
    work = tmp_path_factory.mktemp('crux_search_module')
    fasta = write_fasta(work / 'synthetic_proteome.fasta')
    mzml  = write_mzml(work / 'synthetic.mzML')
    cfg   = loadDefaultConfig()
    out_dir = work / 'comms' / 'results' / 'search'
    ok = tideSearch(
        crux_bin=crux_bin,
        mzml_file=mzml,
        index_dir=built_index,
        out_dir=out_dir,
        fileroot='synthetic',
        config=cfg,
        threads=cfg['search']['threads']
    )
    if not ok:
        pytest.skip('tideSearch failed — cannot run percolator tests')
    target_file = out_dir / 'synthetic.tide-search.target.txt'
    return out_dir, target_file, fasta

# # -- Define tests for running percolator Crux command
# class TestPercolator:
#     def test_creates_psm_output_file(self, crux_bin, search_results, tmp_path):
#         _, target_file, fasta = search_results
#         cfg = loadDefaultConfig()
#         out_dir = tmp_path / 'rescore'
#         ok = percolator(
#             crux_bin=crux_bin,
#             target_psm_file=target_file,
#             database=fasta,
#             out_dir=out_dir,
#             fileroot='synthetic',
#             config=cfg,
#             log_path=tmp_path / 'rescore.log',
#         )
#         assert ok, 'percolator returned False — check rescore.log'
#         psm_target_file = out_dir / 'synthetic.percolator.decoy.psms.txt'
#         psm_decoy_file = out_dir / 'synthetic.percolator.target.psms.txt'
#         assert psm_target_file.exists() and psm_decoy_file.exists()

    # def test_psm_file_has_content(self, crux_bin, search_results, tmp_path):
    #     _, target_file, fasta = search_results
    #     cfg = loadDefaultConfig()
    #     out_dir = tmp_path / 'rescore'
    #     percolator(
    #         crux_bin=crux_bin,
    #         target_psm_file=target_file,
    #         database=fasta,
    #         out_dir=out_dir,
    #         fileroot='synthetic',
    #         config=cfg,
    #     )
    #     psm_file = out_dir / 'synthetic.percolator.psms.txt'
    #     lines = psm_file.read_text().splitlines()
    #     assert len(lines) >= 1

# # -- Define fixture for generating results by running percolator Crux command
# @pytest.fixture(scope='module')
# def percolator_results(crux_bin, search_results, tmp_path_factory):
#     '''Run percolator once per module and return (psm_file, fasta).'''
#     _, target_file, fasta = search_results
#     work = tmp_path_factory.mktemp('crux_rescore_module')
#     cfg = loadDefaultConfig()
#     out_dir = work / 'rescore'
#     ok = percolator(
#         crux_bin=crux_bin,
#         target_psm_file=target_file,
#         database=fasta,
#         out_dir=out_dir,
#         fileroot='synthetic',
#         config=cfg,
#         log_path=work / 'rescore.log',
#     )
#     if not ok:
#         pytest.skip('percolator failed — cannot run spectralCounts tests')
#     psm_file = out_dir / 'synthetic.percolator.psms.txt'
#     return psm_file, fasta

# -- Define tests for running spectral-counts Crux command
class TestSpectralCounts:
    def test_creates_spectral_counts_file(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path):
        psm_file = synthetic_percolator_results / 'EUK' / 'synthetic.EUK.percolator.target.psms.txt'
        cfg = loadDefaultConfig()
        out_dir = tmp_path / 'comms' / 'results' / 'quantify'
        ok = spectralCounts(
            crux_bin=crux_bin,
            psm_file=psm_file,
            database=synthetic_fasta,
            out_dir=out_dir,
            fileroot='synthetic',
            config=cfg,
        )
        assert ok, 'spectralCounts returned False — check quantify.log'
        assert (out_dir / 'synthetic.spectral-counts.target.txt').exists()

    def test_counts_file_has_content(self, crux_bin, synthetic_percolator_results, synthetic_fasta, tmp_path):
        psm_file = synthetic_percolator_results / 'EUK' / 'synthetic.EUK.percolator.target.psms.txt'
        cfg = loadDefaultConfig()
        out_dir = tmp_path / 'comms' / 'results' / 'quantify'
        spectralCounts(
            crux_bin=crux_bin,
            psm_file=psm_file,
            database=synthetic_fasta,
            out_dir=out_dir,
            fileroot='synthetic',
            config=cfg,
        )
        assert (out_dir / 'synthetic.spectral-counts.target.txt').stat().st_size > 0