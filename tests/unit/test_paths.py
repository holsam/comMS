'''
Unit tests for src/comms/utils/paths.py
'''

# -- Import external dependencies
import os, pytest
from pathlib import Path

# -- Import internal functions
from comms.utils.paths import generateOutputFileStructure, checkUniqueFileName, repoBinDir

# -- Define tests for generating output file structure
class TestGenerateOutputFileStructure:
    def test_creates_expected_subdirectory(self, tmp_path):
        result = generateOutputFileStructure(tmp_path, 'search')
        assert result == tmp_path / 'comms' / 'results' / 'search'
        assert result.exists()

    def test_creates_directory_if_absent(self, tmp_path):
        result = generateOutputFileStructure(tmp_path / 'new_dir', 'index')
        assert result.exists()

    def test_returns_existing_path_if_already_correct(self, tmp_path):
        '''If out_dir already ends with comms/results/<command>, return it unchanged.'''
        already_correct = tmp_path / 'comms' / 'results' / 'convert'
        already_correct.mkdir(parents=True)
        result = generateOutputFileStructure(already_correct, 'convert')
        assert result == already_correct

    @pytest.mark.parametrize('command', ['convert', 'index', 'search', 'rescore', 'quantify'])
    def test_all_commands_produce_valid_paths(self, tmp_path, command):
        result = generateOutputFileStructure(tmp_path, command)
        assert result.is_dir()
        assert result.name == command

# -- Define tests for checking unique file names
class TestCheckUniqueFileName:
    def test_returns_expected_name_when_no_conflict(self, tmp_path):
        result = checkUniqueFileName(tmp_path, 'search', orig_name='sample1')
        assert result.name == 'sample1.tide-search.target.txt'

    def test_increments_suffix_on_conflict(self, tmp_path):
        # Create the base file to force a conflict
        base = tmp_path / 'sample1.tide-search.target.txt'
        base.touch()
        result = checkUniqueFileName(tmp_path, 'search', orig_name='sample1')
        assert result.name == 'sample1.tide-search.target-1.txt'

    def test_increments_multiple_times(self, tmp_path):
        for i in ['', '-1', '-2']:
            (tmp_path / f'sample1.tide-search.target{i}.txt').touch()
        result = checkUniqueFileName(tmp_path, 'search', orig_name='sample1')
        assert result.name == 'sample1.tide-search.target-3.txt'

    def test_quantify_naming(self, tmp_path):
        result = checkUniqueFileName(tmp_path, 'quantify', orig_name='sample1')
        assert result.name == 'sample1.spectral-counts.txt'

    def test_rescore_naming(self, tmp_path):
        result = checkUniqueFileName(tmp_path, 'rescore', orig_name='run1')
        assert result.name == 'run1.percolator.psms.txt'

    def test_report_naming_with_format(self, tmp_path):
        result = checkUniqueFileName(tmp_path, 'report', fmt='html')
        assert result.name == 'comms-report.html'

    def test_unknown_command_falls_back_gracefully(self, tmp_path):
        result = checkUniqueFileName(tmp_path, 'unknown_cmd')
        assert 'comms-unknown_cmd-output' in result.name

    def test_returned_path_is_within_out_dir(self, tmp_path):
        result = checkUniqueFileName(tmp_path, 'search', orig_name='s1')
        assert result.parent == tmp_path

# -- Define tests for repoBinDir resolution order
class TestRepoBinDir:
    def test_explicit_experiment_bin_dir_returned_unchanged(self, tmp_path):
        '''An explicit experiment_bin_dir takes priority over everything else'''
        result = repoBinDir(experiment_bin_dir=tmp_path)
        assert result == tmp_path

    def test_explicit_bin_dir_overrides_env_var(self, tmp_path, monkeypatch):
        '''experiment_bin_dir beats COMMS_BIN_DIR even if both are set'''
        env_dir = tmp_path / 'from_env'
        exp_dir = tmp_path / 'from_experiment'
        monkeypatch.setenv('COMMS_BIN_DIR', str(env_dir))
        result = repoBinDir(experiment_bin_dir=exp_dir)
        assert result == exp_dir

    def test_env_var_used_when_no_explicit_dir(self, tmp_path, monkeypatch):
        '''COMMS_BIN_DIR is used when experiment_bin_dir is None'''
        env_dir = tmp_path / 'from_env'
        monkeypatch.setenv('COMMS_BIN_DIR', str(env_dir))
        result = repoBinDir()
        assert result == env_dir

    def test_falls_back_to_repo_walkup_when_nothing_set(self, monkeypatch):
        '''Without either override the repo-root bin/ path is returned'''
        monkeypatch.delenv('COMMS_BIN_DIR', raising=False)
        result = repoBinDir()
        assert result.name == 'bin'

    def test_none_is_the_same_as_no_argument(self, monkeypatch):
        '''Passing experiment_bin_dir=None is equivalent to omitting it'''
        monkeypatch.delenv('COMMS_BIN_DIR', raising=False)
        assert repoBinDir(experiment_bin_dir=None) == repoBinDir()

    def test_returns_path_object(self, tmp_path):
        '''Returned value is Path'''
        result = repoBinDir(experiment_bin_dir=tmp_path)
        assert isinstance(result, Path)