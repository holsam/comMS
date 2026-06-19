'''
comMS motif extension: MEME suite wrapper tests
'''

# -- Import external dependencies
import pytest, subprocess
from pathlib import Path

# -- Import motif/utils/meme.py
from comms.ext.motif.utils import meme

# -- Define test class for binary discovery
class TestMemeBinaryDiscovery:
    def test_version_parsing():
        assert meme._parse_version('MEME version 5.5.5 (Release ...)') == (5, 5, 5)
        assert meme._parse_version('streme 5.4.1') == (5, 4, 1)
        assert meme._parse_version('no version here') is None

    def test_require_streme_rejects_old(monkeypatch):
        install = meme.MemeInstall(bin_dir=Path('/x'), version=(4, 11, 0))
        with pytest.raises(meme.MemeVersionError):
            meme.require_streme(install)

    def test_find_meme_missing(monkeypatch):
        monkeypatch.setattr(meme.shutil, 'which', lambda _: None)
        monkeypatch.setattr(meme.platform, 'system', lambda: 'Linux')
        with pytest.raises(meme.MemeNotFoundError):
            meme.find_meme(hint=Path('/definitely/not/here'))

    def test_parse_minimal_meme(tmp_path):
        meme = tmp_path / 'm.meme'
        meme.write_text(
            'MEME version 5\n\n'
            'ALPHABET= ACDEFGHIKLMNPQRSTVWY\n\n'
            'MOTIF M1 STREME-1\n'
            'letter-probability matrix: alength= 20 w= 2 nsites= 10 E= 1e-3\n'
            + ' '.join(['0.05'] * 20) + '\n'
            + ' '.join(['0.05'] * 20) + '\n'
        )
        motifs = meme.parse_minimal_meme(meme)
        assert len(motifs) == 1
        assert motifs[0].width == 2 and motifs[0].nsites == 10