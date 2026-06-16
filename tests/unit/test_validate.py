'''
Unit tests for src/comms/utils/validate.py
'''

# -- Import external dependencies
import contextlib, logging, pytest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# -- Import functions under test
from comms.utils.validate import (
    validate,
    _parse_version,
    _find_all_crux,
    _find_all_trfp,
    _select_best,
    _get_crux_version,
    _get_trfp_version,
    _check_crux,
    _check_trfp,
    _CRUX_MIN_LFQ,
    _TRFP_MIN_MONO,
)

# -- Import logMsg from utils/log.py
from comms.utils.log import logMsg

# -- Define helper functions
# -- _crux_version_output: returns a string mocking crux version command
def _crux_version_output(version: str) -> str:
    '''Return a mock `crux version` stdout string containing the given version.'''
    return (
        'INFO: Beginning version.\n'
        '====================\n'
        f'Crux version {version}-abc123-2025-01-01\n'
        '====================\n'
        'INFO: Return Code:0\n'
    )
# -- _fake_bin: return a Path to a fake binary
def _fake_bin(tmp_path: Path, name: str) -> Path:
    '''Write a zero-byte placeholder binary and return its path.'''
    p = tmp_path / name
    p.touch()
    return p

# -- Define tests for _parse_version helper function
class TestParseVersion:
    def test_parses_three_part_version(self):
        assert _parse_version('4.3.2') == (4, 3, 2)

    def test_parses_two_part_version(self):
        assert _parse_version('1.4') == (1, 4)

    def test_parses_version_embedded_in_longer_string(self):
        assert _parse_version('Crux version 4.3.2-abc123') == (4, 3, 2)

    def test_returns_none_for_no_digits(self):
        assert _parse_version('no version here') is None

    def test_returns_none_for_empty_string(self):
        assert _parse_version('') is None

    def test_returns_tuple_of_ints(self):
        result = _parse_version('1.2.3')
        assert all(isinstance(v, int) for v in result)

    def test_version_comparison_works_correctly(self):
        assert _parse_version('5.0.0') >= _CRUX_MIN_LFQ
        assert _parse_version('4.3.2') < _CRUX_MIN_LFQ

# -- Define tests for _find_all_crux helper function
class TestFindAllCrux:
    def test_returns_empty_list_when_no_installations(self, tmp_path):
        assert _find_all_crux(tmp_path) == []

    def test_returns_single_installation(self, tmp_path):
        binary = tmp_path / 'crux-4.3.2.Linux.x86_64' / 'bin' / 'crux'
        binary.parent.mkdir(parents=True)
        binary.touch()
        assert _find_all_crux(tmp_path) == [binary]

    def test_returns_multiple_installations(self, tmp_path):
        for version in ('4.3.2', '5.0.0'):
            binary = tmp_path / f'crux-{version}.Linux.x86_64' / 'bin' / 'crux'
            binary.parent.mkdir(parents=True)
            binary.touch()
        result = _find_all_crux(tmp_path)
        assert len(result) == 2

    def test_returns_list_of_paths(self, tmp_path):
        binary = tmp_path / 'crux-4.3.2.Linux.x86_64' / 'bin' / 'crux'
        binary.parent.mkdir(parents=True)
        binary.touch()
        result = _find_all_crux(tmp_path)
        assert all(isinstance(p, Path) for p in result)

# -- Define tests for _find_all_trfp helper function
class TestFindAllTrfp:
    def test_returns_empty_list_when_no_installations(self, tmp_path):
        assert _find_all_trfp(tmp_path) == []

    def test_finds_legacy_exe_binary(self, tmp_path):
        binary = tmp_path / 'ThermoRawFileParser-1.4.5' / 'ThermoRawFileParser.exe'
        binary.parent.mkdir(parents=True)
        binary.touch()
        assert binary in _find_all_trfp(tmp_path)

    def test_finds_native_binary_without_exe_extension(self, tmp_path):
        binary = tmp_path / 'ThermoRawFileParser-2.0.0' / 'ThermoRawFileParser'
        binary.parent.mkdir(parents=True)
        binary.touch()
        assert binary in _find_all_trfp(tmp_path)

    def test_finds_both_legacy_and_native_together(self, tmp_path):
        legacy = tmp_path / 'ThermoRawFileParser-1.4.5' / 'ThermoRawFileParser.exe'
        native = tmp_path / 'ThermoRawFileParser-2.0.0' / 'ThermoRawFileParser'
        for p in (legacy, native):
            p.parent.mkdir(parents=True)
            p.touch()
        result = _find_all_trfp(tmp_path)
        assert legacy in result
        assert native in result

    def test_returns_list_of_paths(self, tmp_path):
        binary = tmp_path / 'ThermoRawFileParser-1.4.5' / 'ThermoRawFileParser.exe'
        binary.parent.mkdir(parents=True)
        binary.touch()
        assert all(isinstance(p, Path) for p in _find_all_trfp(tmp_path))

# -- Define tests for _select_best helper function
class TestSelectBest:
    def _versions(self, mapping: dict[str, tuple]) -> callable:
        '''Return a get_version_fn that maps path name to version tuple.'''
        return lambda p: mapping.get(p.name)

    def test_returns_none_when_no_candidates(self):
        assert _select_best([], lambda p: (1, 0, 0)) is None

    def test_returns_none_when_all_versions_unparseable(self, tmp_path):
        candidates = [_fake_bin(tmp_path, 'a'), _fake_bin(tmp_path, 'b')]
        assert _select_best(candidates, lambda p: None) is None

    def test_returns_single_candidate(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'crux')
        result = _select_best([candidate], lambda p: (4, 3, 2))
        assert result == (candidate, (4, 3, 2))

    def test_selects_highest_version(self, tmp_path):
        old = _fake_bin(tmp_path, 'old')
        new = _fake_bin(tmp_path, 'new')
        versions = {'old': (4, 3, 2), 'new': (5, 0, 0)}
        result = _select_best([old, new], self._versions(versions))
        assert result == (new, (5, 0, 0))

    def test_skips_candidate_with_unparseable_version(self, tmp_path):
        good = _fake_bin(tmp_path, 'good')
        bad = _fake_bin(tmp_path, 'bad')
        versions = {'good': (4, 3, 2), 'bad': None}
        result = _select_best([good, bad], self._versions(versions))
        assert result == (good, (4, 3, 2))

    def test_returns_path_and_version_tuple(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'crux')
        path, version = _select_best([candidate], lambda p: (4, 3, 2))
        assert isinstance(path, Path)
        assert isinstance(version, tuple)

    def test_order_of_candidates_does_not_affect_result(self, tmp_path):
        a = _fake_bin(tmp_path, 'a')
        b = _fake_bin(tmp_path, 'b')
        versions = {'a': (5, 0, 0), 'b': (4, 3, 2)}
        get_v = self._versions(versions)
        assert _select_best([a, b], get_v) == _select_best([b, a], get_v)

# -- Define tests for _get_crux_version helper function
class TestGetCruxVersion:
    def test_parses_well_formed_output(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout=_crux_version_output('4.3.2'), stderr='', returncode=0,
            )
            result = _get_crux_version(tmp_path / 'crux')
        assert result == (4, 3, 2)

    def test_returns_none_when_no_version_line(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='INFO: nothing useful here\n', stderr='', returncode=0,
            )
            result = _get_crux_version(tmp_path / 'crux')
        assert result is None

    def test_returns_none_when_subprocess_raises(self, tmp_path):
        with patch('subprocess.run', side_effect=OSError('binary not found')):
            result = _get_crux_version(tmp_path / 'crux')
        assert result is None

    def test_parses_version_from_stderr_as_fallback(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='', stderr=_crux_version_output('5.1.0'), returncode=0,
            )
            result = _get_crux_version(tmp_path / 'crux')
        assert result == (5, 1, 0)

# -- Define tests for _get_trfp_version helper function
class TestGetTrfpVersion:
    def test_parses_plain_version_string(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='1.4.5', stderr='', returncode=0,
            )
            result = _get_trfp_version(tmp_path / 'ThermoRawFileParser.exe')
        assert result == (1, 4, 5)

    def test_returns_none_when_output_unparseable(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='no version here', stderr='', returncode=0,
            )
            result = _get_trfp_version(tmp_path / 'ThermoRawFileParser.exe')
        assert result is None

    def test_returns_none_when_subprocess_raises(self, tmp_path):
        with patch('subprocess.run', side_effect=OSError('not found')):
            result = _get_trfp_version(tmp_path / 'ThermoRawFileParser.exe')
        assert result is None

# -- Define tests for _check_crux helper function
class TestCheckCrux:
    '''Define ficture to initialise logging'''
    @pytest.fixture(autouse=True)
    def init_logmsg(self):
        logMsg('validate')

    def _patches(
        self,
        bin_dir: Path,
        candidates: list[Path],
        versions: dict[str, tuple | None],
    ):  
        '''Return an ExitStack with all necessary patches applied.'''
        def _get_v(p):
            return versions.get(p.name)
        stack = contextlib.ExitStack()
        stack.enter_context(patch('comms.utils.validate._find_all_crux', return_value=candidates))
        stack.enter_context(patch('comms.utils.validate._get_crux_version', side_effect=_get_v))
        return stack

    def test_raises_when_no_candidates_found(self, tmp_path):
        with patch('comms.utils.validate._find_all_crux', return_value=[]):
            with pytest.raises(SystemExit):
                _check_crux(tmp_path, allow_lfq=False)

    def test_raises_when_all_versions_unparseable(self, tmp_path):
        candidates = [_fake_bin(tmp_path, 'crux')]
        with self._patches(tmp_path, candidates, {'crux': None}):
            with pytest.raises(SystemExit):
                _check_crux(tmp_path, allow_lfq=False)

    def test_returns_path_for_single_installation(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'crux')
        with self._patches(tmp_path, [candidate], {'crux': (4, 3, 2)}):
            result = _check_crux(tmp_path, allow_lfq=False)
        assert result == candidate

    def test_returns_highest_versioned_path_for_multiple_installations(self, tmp_path):
        old = _fake_bin(tmp_path, 'crux_old')
        new = _fake_bin(tmp_path, 'crux_new')
        with self._patches(tmp_path, [old, new], {'crux_old': (4, 3, 2), 'crux_new': (5, 0, 0)}):
            result = _check_crux(tmp_path, allow_lfq=False)
        assert result == new

    def test_logs_info_message_when_multiple_found(self, tmp_path, caplog):
        old = _fake_bin(tmp_path, 'crux_old')
        new = _fake_bin(tmp_path, 'crux_new')
        with self._patches(tmp_path, [old, new], {'crux_old': (4, 3, 2), 'crux_new': (5, 0, 0)}), \
             caplog.at_level(logging.INFO):
            _check_crux(tmp_path, allow_lfq=False)
        assert '2 Crux installations found' in caplog.text

    def test_no_log_message_for_single_installation(self, tmp_path, caplog):
        candidate = _fake_bin(tmp_path, 'crux')
        with self._patches(tmp_path, [candidate], {'crux': (4, 3, 2)}), \
             caplog.at_level(logging.INFO):
            _check_crux(tmp_path, allow_lfq=False)
        assert 'Crux installations found' not in caplog.text

    def test_allow_lfq_raises_when_best_version_below_minimum(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'crux')
        with self._patches(tmp_path, [candidate], {'crux': (4, 3, 2)}):
            with pytest.raises(SystemExit):
                _check_crux(tmp_path, allow_lfq=True)

    def test_allow_lfq_passes_when_best_version_meets_minimum(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'crux')
        with self._patches(tmp_path, [candidate], {'crux': _CRUX_MIN_LFQ}):
            _check_crux(tmp_path, allow_lfq=True)    # should not raise

    def test_allow_lfq_false_does_not_enforce_minimum(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'crux')
        with self._patches(tmp_path, [candidate], {'crux': (1, 0, 0)}):
            _check_crux(tmp_path, allow_lfq=False)    # should not raise

    def test_get_version_called_for_every_candidate(self, tmp_path):
        candidates = [_fake_bin(tmp_path, f'crux_{i}') for i in range(3)]
        with patch('comms.utils.validate._find_all_crux', return_value=candidates), \
             patch('comms.utils.validate._get_crux_version', return_value=(4, 3, 2)) as mock_v:
            _check_crux(tmp_path, allow_lfq=False)
        assert mock_v.call_count == 3

# -- Define tests for _check_trfp helper function
class TestCheckTrfp:
    '''Define ficture to initialise logging'''
    @pytest.fixture(autouse=True)
    def init_logmsg(self):
        logMsg('validate')    

    def _patches(
        self,
        bin_dir: Path,
        candidates: list[Path],
        versions: dict[str, tuple | None],
        system: str = 'Linux',
        mono: str | None = '/usr/bin/mono',
    ):
        def _get_v(p):
            return versions.get(p.name)
        stack = contextlib.ExitStack()
        stack.enter_context(patch('comms.utils.validate._find_all_trfp', return_value=candidates))
        stack.enter_context(patch('comms.utils.validate._get_trfp_version', side_effect=_get_v))
        stack.enter_context(patch('comms.utils.validate.platform.system', return_value=system))
        stack.enter_context(patch('comms.utils.validate.shutil.which', return_value=mono))
        return stack

    def test_raises_when_no_candidates_found(self, tmp_path):
        with patch('comms.utils.validate._find_all_trfp', return_value=[]):
            with pytest.raises(SystemExit):
                _check_trfp(tmp_path)

    def test_raises_when_all_versions_unparseable(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        with self._patches(tmp_path, [candidate], {'ThermoRawFileParser.exe': None}):
            with pytest.raises(SystemExit):
                _check_trfp(tmp_path)

    def test_returns_path_for_single_installation(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser')
        with self._patches(tmp_path, [candidate], {'ThermoRawFileParser': (2, 0, 0)}):
            result = _check_trfp(tmp_path)
        assert result == candidate

    def test_returns_highest_versioned_path_for_multiple_installations(self, tmp_path):
        old = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        new = _fake_bin(tmp_path, 'ThermoRawFileParser')
        versions = {'ThermoRawFileParser.exe': (1, 4, 5), 'ThermoRawFileParser': (2, 0, 0)}
        with self._patches(tmp_path, [old, new], versions):
            result = _check_trfp(tmp_path)
        assert result == new

    def test_logs_info_message_when_multiple_found(self, tmp_path, caplog):
        old = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        new = _fake_bin(tmp_path, 'ThermoRawFileParser')
        versions = {'ThermoRawFileParser.exe': (1, 4, 5), 'ThermoRawFileParser': (2, 0, 0)}
        with self._patches(tmp_path, [old, new], versions), caplog.at_level(logging.INFO):
            _check_trfp(tmp_path)
        assert '2 ThermoRawFileParser installations found' in caplog.text

    def test_no_message_logged_when_single_installation(self, tmp_path, capsys):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser')
        with self._patches(tmp_path, [candidate], {'ThermoRawFileParser': (2, 0, 0)}):
            _check_trfp(tmp_path)
        captured = capsys.readouterr()
        assert 'installations' not in captured.out.lower()

    def test_does_not_raise_when_version_at_mono_threshold(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser')
        with self._patches(tmp_path, [candidate], {'ThermoRawFileParser': _TRFP_MIN_MONO}):
            _check_trfp(tmp_path)    # should not raise

    def test_raises_when_below_mono_threshold_on_linux_without_mono(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        with self._patches(
            tmp_path, [candidate], {'ThermoRawFileParser.exe': (1, 4, 5)},
            system='Linux', mono=None,
        ):
            with pytest.raises(SystemExit):
                _check_trfp(tmp_path)

    def test_does_not_raise_when_below_threshold_on_linux_with_mono(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        with self._patches(
            tmp_path, [candidate], {'ThermoRawFileParser.exe': (1, 4, 5)},
            system='Linux', mono='/usr/bin/mono',
        ):
            _check_trfp(tmp_path)    # should not raise

    def test_does_not_raise_when_below_threshold_on_windows(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        with self._patches(
            tmp_path, [candidate], {'ThermoRawFileParser.exe': (1, 4, 5)},
            system='Windows', mono=None,
        ):
            _check_trfp(tmp_path)    # should not raise

    def test_does_not_raise_when_below_threshold_on_macos_with_mono(self, tmp_path):
        candidate = _fake_bin(tmp_path, 'ThermoRawFileParser.exe')
        with self._patches(
            tmp_path, [candidate], {'ThermoRawFileParser.exe': (1, 4, 5)},
            system='Darwin', mono='/opt/homebrew/bin/mono',
        ):
            _check_trfp(tmp_path)    # should not raise

    def test_get_version_called_for_every_candidate(self, tmp_path):
        candidates = [_fake_bin(tmp_path, f'TRFP_{i}') for i in range(3)]
        with patch('comms.utils.validate._find_all_trfp', return_value=candidates), \
             patch('comms.utils.validate._get_trfp_version', return_value=(2, 0, 0)) as mock_v, \
             patch('comms.utils.validate.platform.system', return_value='Linux'), \
             patch('comms.utils.validate.shutil.which', return_value='/usr/bin/mono'):
            _check_trfp(tmp_path)
        assert mock_v.call_count == 3

# -- Define tests for validate function
class TestValidate:
    '''Define ficture to initialise logging'''
    @pytest.fixture(autouse=True)
    def init_logmsg(self):
        logMsg('validate')

    def _patches(
        self,
        crux_candidates: list[Path] | None = None,
        crux_version: tuple = (4, 3, 2),
        trfp_candidates: list[Path] | None = None,
        trfp_version: tuple = (2, 0, 0),
        system: str = 'Linux',
        mono: str | None = '/usr/bin/mono',
        bin_dir: Path = Path('/fake/bin'),
    ):
        # crux_candidates = crux_candidates or [Path('/fake/bin/crux')]
        # trfp_candidates = trfp_candidates or [Path('/fake/bin/ThermoRawFileParser')]
        stack = contextlib.ExitStack()
        stack.enter_context(patch('comms.utils.validate.pathutil.repoBinDir', return_value=bin_dir))
        stack.enter_context(patch('comms.utils.validate._find_all_crux', return_value=crux_candidates))
        stack.enter_context(patch('comms.utils.validate._get_crux_version', return_value=crux_version))
        stack.enter_context(patch('comms.utils.validate._find_all_trfp', return_value=trfp_candidates))
        stack.enter_context(patch('comms.utils.validate._get_trfp_version', return_value=trfp_version))
        stack.enter_context(patch('comms.utils.validate.platform.system', return_value=system))
        stack.enter_context(patch('comms.utils.validate.shutil.which', return_value=mono))
        return stack

    def test_returns_none_none_when_no_checks_requested(self):
        crux_bin, trfp_path = validate()
        assert crux_bin is None
        assert trfp_path is None

    def test_noop_when_no_checks_requested_does_not_call_find(self):
        with patch('comms.utils.validate._find_all_crux') as mock_find:
            validate()
        mock_find.assert_not_called()

    def test_returns_crux_bin_when_check_crux(self):
        fake_crux = Path('/fake/bin/crux')
        with self._patches(crux_candidates=[fake_crux]):
            crux_bin, trfp_path = validate(check_crux=True)
        assert crux_bin == fake_crux
        assert trfp_path is None

    def test_returns_trfp_path_when_check_trfp(self):
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(trfp_candidates=[fake_trfp]):
            crux_bin, trfp_path = validate(check_trfp=True)
        assert crux_bin is None
        assert trfp_path == fake_trfp

    def test_returns_both_when_both_checked(self):
        fake_crux = Path('/fake/bin/crux')
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(crux_candidates=[fake_crux], trfp_candidates=[fake_trfp]):
            crux_bin, trfp_path = validate(check_crux=True, check_trfp=True)
        assert crux_bin == fake_crux
        assert trfp_path == fake_trfp

    def test_crux_not_found_raises(self):
        with self._patches(crux_candidates=None):
            with pytest.raises(SystemExit):
                validate(check_crux=True)

    def test_trfp_not_found_raises(self):
        with self._patches(trfp_candidates=None):
            with pytest.raises(SystemExit):
                validate(check_trfp=True)

    def test_allow_lfq_raises_for_old_crux(self):
        with self._patches(crux_version=(4, 3, 2)):
            with pytest.raises(SystemExit):
                validate(check_crux=True, allow_lfq=True)

    def test_allow_lfq_passes_for_crux_at_minimum(self):
        fake_crux = Path('/fake/bin/crux')
        with self._patches(crux_candidates=[fake_crux], crux_version=_CRUX_MIN_LFQ):
            validate(check_crux=True, allow_lfq=True)    # should not raise

    def test_trfp_old_version_no_mono_raises(self):
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(trfp_candidates=[fake_trfp], trfp_version=(1, 4, 5), system='Linux', mono=None):
            with pytest.raises(SystemExit):
                validate(check_trfp=True)

    def test_trfp_old_version_with_mono_does_not_raise(self):
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(trfp_candidates=[fake_trfp], trfp_version=(1, 4, 5), system='Linux', mono='/usr/bin/mono'):
            validate(check_trfp=True)    # should not raise

    def test_trfp_old_version_windows_does_not_raise(self):
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(trfp_candidates=[fake_trfp], trfp_version=(1, 4, 5), system='Windows', mono=None):
            validate(check_trfp=True)    # should not raise

    def test_find_all_crux_not_called_when_check_crux_false(self):
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(trfp_candidates=[fake_trfp]):
            with patch('comms.utils.validate._find_all_crux') as mock_find:
                validate(check_trfp=True)
        mock_find.assert_not_called()

    def test_find_all_trfp_not_called_when_check_trfp_false(self):
        fake_crux = Path('/fake/bin/crux')
        with self._patches(crux_candidates=[fake_crux]):
            with patch('comms.utils.validate._find_all_trfp') as mock_find:
                validate(check_crux=True)
        mock_find.assert_not_called()

    def test_error_message_logged_on_crux_not_found(self, caplog):
        with self._patches(crux_candidates=None), caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                validate(check_crux=True)
        assert any(r.levelno >= logging.ERROR for r in caplog.records)

    def test_error_message_logged_on_lfq_version_too_old(self, caplog):
        fake_crux = Path('/fake/bin/crux')
        with self._patches(crux_candidates=[fake_crux], crux_version=(4, 3, 2)), \
             caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                validate(check_crux=True, allow_lfq=True)
        assert any(r.levelno >= logging.ERROR for r in caplog.records)
        assert 'not support lfq' in caplog.text
        
    def test_error_message_logged_on_mono_absent(self, caplog):
        fake_trfp = Path('/fake/bin/ThermoRawFileParser')
        with self._patches(trfp_candidates=[fake_trfp], trfp_version=(1, 4, 5), system='Linux', mono=None), \
             caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                validate(check_trfp=True)
        assert any(r.levelno >= logging.ERROR for r in caplog.records)
        assert 'Mono not found' in caplog.text