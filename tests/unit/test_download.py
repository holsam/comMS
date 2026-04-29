'''
Unit tests for src/comms/utils.download.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import internal functions
from comms.utils.download import CRUX_DEFAULT_VERSION, TRFP_DEFAULT_VERSION, _detect_platform, _resolve_bin_dir, _TRFP_DOWNLOAD_URL, _CRUX_DOWNLOAD_BASE, _CRUX_PLATFORM_MAP

# -- Define tests (sanity checks) for constants
class TestConstants:
    def test_default_versions_are_strings(self):
        assert isinstance(CRUX_DEFAULT_VERSION, str)
        assert isinstance(TRFP_DEFAULT_VERSION, str)

    def test_default_versions_non_empty(self):
        assert CRUX_DEFAULT_VERSION.strip()
        assert TRFP_DEFAULT_VERSION.strip()

    def test_trfp_url_template_contains_version_placeholder(self):
        assert '{version}' in _TRFP_DOWNLOAD_URL

    def test_trfp_url_template_produces_valid_url(self):
        url = _TRFP_DOWNLOAD_URL.format(version=TRFP_DEFAULT_VERSION)
        assert url.startswith('https://')
        assert TRFP_DEFAULT_VERSION in url

    def test_crux_platform_map_keys_are_tuples(self):
        for k in _CRUX_PLATFORM_MAP:
            assert isinstance(k, tuple) and len(k) == 2

    def test_crux_download_base_is_https(self):
        assert _CRUX_DOWNLOAD_BASE.startswith('https://')

# -- Define tests for _detect_platform helper function
class TestDetectPlatform:
    def test_returns_two_strings(self):
        system, machine = _detect_platform()
        assert isinstance(system, str)
        assert isinstance(machine, str)

    def test_system_is_recognised(self):
        system, _ = _detect_platform()
        assert system in ('Linux', 'Darwin', 'Windows', 'Java'), (
            f'Unexpected platform system: {system}'
        )

# -- Define tests for _resolve_bin_dir helper function
class TestResolveBinDir:
    def test_returns_override_when_provided(self, tmp_path):
        result = _resolve_bin_dir(override=tmp_path)
        assert result == tmp_path

    def test_returns_path_object(self, tmp_path):
        assert isinstance(_resolve_bin_dir(override=tmp_path), Path)

    def test_falls_back_to_repoBinDir_when_no_override(self):
        '''
        When override is None, _resolve_bin_dir should be <repo-root>/bin
        '''
        result = _resolve_bin_dir(override=None)
        assert str(result).endswith('/bin')

# -- Define tests for correctly constructing crux tarball URL
class TestCruxUrlConstruction:
    @pytest.mark.parametrize('platform_key,expected_stem', [
        (('Linux',  'x86_64'), f'crux-{CRUX_DEFAULT_VERSION}.Linux.x86_64'),
        (('Darwin', 'x86_64'), f'crux-{CRUX_DEFAULT_VERSION}.Darwin.x86_64'),
        (('Darwin', 'arm64'),  f'crux-{CRUX_DEFAULT_VERSION}.Darwin.arm64'),
    ])
    def test_tarball_name_for_known_platforms(self, platform_key, expected_stem):
        crux_platform, crux_arch = _CRUX_PLATFORM_MAP[platform_key]
        stem = f'crux-{CRUX_DEFAULT_VERSION}.{crux_platform}.{crux_arch}'
        assert stem == expected_stem

    def test_download_crux_raises_not_implemented_on_windows(self, monkeypatch):
        import comms.utils.download as dl
        monkeypatch.setattr(dl, '_detect_platform', lambda: ('Windows', 'x86_64'))
        with pytest.raises(NotImplementedError):
            dl.download_crux(bin_dir=Path('/tmp'))

    def test_download_crux_raises_runtime_on_unknown_platform(self, monkeypatch, tmp_path):
        import comms.utils.download as dl
        monkeypatch.setattr(dl, '_detect_platform', lambda: ('FreeBSD', 'x86_64'))
        with pytest.raises(RuntimeError, match='Unrecognised platform'):
            dl.download_crux(bin_dir=tmp_path)