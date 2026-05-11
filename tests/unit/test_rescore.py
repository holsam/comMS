'''
Unit tests for helper functions in src/comms/commands/rescore.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import functions under test
from comms.commands.rescore import _parseOrganismTags, _mergeTypeRescoredPsms, _mergeRescoredPsms

# -- Define constants
PSM_HEADER = 'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
PSM_ROW_TE = 'synthetic_1\t1.5\t0.001\t0.001\tK.ACDEFGHIK.L\tsp|TE001|GENE1_TESTEUK\n'
PSM_ROW_TP = 'synthetic_2\t1.2\t0.005\t0.003\tK.SAMPLEK.T\tsp|TP001|GENE1_TESTPRO\n'

# -- Define helper functions
def _write_psm_file(path: Path, rows: list[str]) -> None:
    '''Write a synthetic Percolator file with standard header'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PSM_HEADER + ''.join(rows))

def _make_psm_files(out_dir: Path, file_base: str, subfastas: dict) -> None:
    '''
    Write synthetic target and decoy PSM files for each organism label in the directory structure expected by _mergeTypeRescoredPsms:
        out_dir/<label>/<file_base>.<label>.percolator.<type>.psms.txt
    '''
    rows = {'EUK': [PSM_ROW_TE], 'PRO': [PSM_ROW_TP]}
    for label in subfastas.keys():
        for match_type in ('target', 'decoy'):
            path = out_dir / label / f'{file_base}.{label}.percolator.{match_type}.psms.txt'
            _write_psm_file(path, rows[label])

# -- Define unit tests for _parseOrganismTags helper function

class TestParseOrganismTags:
    def test_parses_two_organism_string(self):
        result = _parseOrganismTags('EUK,TESTEUK,PRO,TESTPRO')
        assert result == {'EUK': 'TESTEUK', 'PRO': 'TESTPRO'}

    def test_parses_single_organism_string(self):
        result = _parseOrganismTags('EUK,TESTEUK')
        assert result == {'EUK': 'TESTEUK'}

    def test_strips_spaces_around_commas(self):
        result = _parseOrganismTags('EUK, TESTEUK, PRO, TESTPRO')
        assert result == {'EUK': 'TESTEUK', 'PRO': 'TESTPRO'}

    def test_strips_leading_and_trailing_whitespace(self):
        result = _parseOrganismTags('  EUK,TESTEUK  ')
        assert result == {'EUK': 'TESTEUK'}

    def test_preserves_regex_characters_in_values(self):
        result = _parseOrganismTags('EUK,TESTEUK$')
        assert result['EUK'] == 'TESTEUK$'

    def test_odd_count_raises_system_exit(self):
        with pytest.raises(SystemExit):
            _parseOrganismTags('EUK,TESTEUK,PRO')

    def test_single_item_raises_system_exit(self):
        with pytest.raises(SystemExit):
            _parseOrganismTags('EUK')

    def test_empty_string_raises_system_exit(self):
        with pytest.raises(SystemExit):
            _parseOrganismTags('')

    def test_returns_dict(self):
        result = _parseOrganismTags('EUK,TESTEUK')
        assert isinstance(result, dict)

    def test_keys_and_values_are_strings(self):
        result = _parseOrganismTags('EUK,TESTEUK,PRO,TESTPRO')
        for k, v in result.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

# -- Define unit tests for _mergeTypedRescoredPsms helper function
class TestMergeTypeRescoredPsms:
    @pytest.fixture()
    def setup(self, tmp_path):
        '''Write synthetic PSM files for two organisms and return (out_dir, subfastas).'''
        subfastas = {'EUK': tmp_path / 'EUK.fa', 'PRO': tmp_path / 'PRO.fa'}
        _make_psm_files(tmp_path, 'synthetic', subfastas)
        return tmp_path, subfastas

    def test_returns_list(self, setup):
        out_dir, subfastas = setup
        result = _mergeTypeRescoredPsms('target', 'synthetic', subfastas, out_dir)
        assert isinstance(result, list)

    def test_all_elements_end_with_newline(self, setup):
        out_dir, subfastas = setup
        result = _mergeTypeRescoredPsms('target', 'synthetic', subfastas, out_dir)
        for element in result:
            assert element.endswith('\n'), f'Element does not end with newline: {element}'

    def test_header_appears_exactly_once(self, setup):
        out_dir, subfastas = setup
        result = _mergeTypeRescoredPsms('target', 'synthetic', subfastas, out_dir)
        header_lines = [line for line in result if line.startswith('PSMId\t')]
        assert len(header_lines) == 1

    def test_rows_from_both_organisms_present(self, setup):
        out_dir, subfastas = setup
        result = _mergeTypeRescoredPsms('target', 'synthetic', subfastas, out_dir)
        data_rows = [line for line in result if not line.startswith('PSMId\t')]
        labels = {row.split('\t')[-1] for row in data_rows}
        assert any('EUK' in label for label in labels)
        assert any('PRO' in label for label in labels)

    def test_works_for_decoy_type(self, setup):
        out_dir, subfastas = setup
        result = _mergeTypeRescoredPsms('decoy', 'synthetic', subfastas, out_dir)
        assert isinstance(result, list)
        assert len(result) > 0

# -- Define unit tests for _mergeRescoredPsms helper function
class TestMergeRescoredPsms:
    @pytest.fixture()
    def setup(self, tmp_path):
        subfastas = {'EUK': tmp_path / 'EUK.fa', 'PRO': tmp_path / 'PRO.fa'}
        _make_psm_files(tmp_path, 'synthetic', subfastas)
        return tmp_path, subfastas

    def test_returns_true_on_success(self, setup):
        out_dir, subfastas = setup
        result = _mergeRescoredPsms('synthetic', subfastas, out_dir)
        assert result is True

    def test_returns_false_when_input_file_missing(self, tmp_path):
        subfastas = {'EUK': tmp_path / 'EUK.fa'}
        result = _mergeRescoredPsms('synthetic', subfastas, tmp_path)
        assert result is False

    def test_writes_target_merged_file(self, setup):
        out_dir, subfastas = setup
        _mergeRescoredPsms('synthetic', subfastas, out_dir)
        assert (out_dir / 'synthetic.percolator.target.psms.txt').exists()

    def test_writes_decoy_merged_file(self, setup):
        out_dir, subfastas = setup
        _mergeRescoredPsms('synthetic', subfastas, out_dir)
        assert (out_dir / 'synthetic.percolator.decoy.psms.txt').exists()

    def test_merged_target_file_is_non_empty(self, setup):
        out_dir, subfastas = setup
        _mergeRescoredPsms('synthetic', subfastas, out_dir)
        assert (out_dir / 'synthetic.percolator.target.psms.txt').stat().st_size > 0

    def test_merged_file_is_readable_text(self, setup):
        out_dir, subfastas = setup
        _mergeRescoredPsms('synthetic', subfastas, out_dir)
        content = (out_dir / 'synthetic.percolator.target.psms.txt').read_text()
        assert isinstance(content, str)
        assert len(content) > 0
