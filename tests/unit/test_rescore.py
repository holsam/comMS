'''
Unit tests for helper functions in src/comms/commands/rescore.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import functions under test
from comms.commands.rescore import _parseOrganismTags, _classifyPsmRow, _splitPsmsByOrganism

# -- Define constants
PSM_HEADER = 'scan\tcharge\tspectrum precursor m/z\tpeptide\tflanking aa\tprotein id\n'
PSM_ROW_EUK = '1\t2\t500.0\tACDEFGHIK\tAK\tsp|TE001|GENE1_TESTEUK\n'
PSM_ROW_PRO = '2\t2\t400.0\tSAMPLEK\tTK\tsp|TP001|GENE1_TESTPRO\n'
PSM_ROW_CONT = '3\t2\t300.0\tPEPTIDEFK\tSK\tcRAP|CONT001|CONT\n'
ORGANISM_TAGS = {'EUK': 'TESTEUK', 'PRO': 'TESTPRO'}

# -- Define helper function to write a combined Percolator PSM file
def _write_combined_psm(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PSM_HEADER + ''.join(rows))

# -- Define tests for _parseOrganismTags helper function
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


# -- Define tests for _classifyPsmRow helper function
class TestClassifyPsmRow:
    def test_returns_list_for_matching_row(self):
        result = _classifyPsmRow(row=PSM_ROW_EUK, id_index=5, organism_tags=ORGANISM_TAGS)
        assert isinstance(result, list)

    def test_returns_correct_label_for_euk_row(self):
        assert _classifyPsmRow(row=PSM_ROW_EUK, id_index=5, organism_tags=ORGANISM_TAGS) == ['EUK']

    def test_returns_correct_label_for_pro_row(self):
        assert _classifyPsmRow(row=PSM_ROW_PRO, id_index=5, organism_tags=ORGANISM_TAGS) == ['PRO']

    def test_returns_contaminants_list_for_unmatched_row(self):
        assert _classifyPsmRow(row=PSM_ROW_CONT, id_index=5, organism_tags=ORGANISM_TAGS) == ['contaminants']

    def test_returns_contaminants_list_for_empty_row(self):
        assert _classifyPsmRow(row='', id_index=5, organism_tags=ORGANISM_TAGS) == ['contaminants']

    def test_uses_last_column_for_protein_id(self):
        row = 'id\t1.0\t0.01\t0.001\tK.PEP.K\tsp|TE001|GENE1_TESTEUK\n'
        assert _classifyPsmRow(row=row, id_index=5, organism_tags=ORGANISM_TAGS) == ['EUK']

    def test_returns_multiple_labels_for_shared_psm(self):
        overlapping_tags = {'EUK': 'TESTEUK', 'ALSO': 'TESTEUK'}
        result = _classifyPsmRow(row=PSM_ROW_EUK, id_index=5, organism_tags=overlapping_tags)
        assert isinstance(result, list)
        assert len(result) == 2
        assert 'EUK' in result and 'ALSO' in result

# -- Define tests for _splitPsmsByOrganism helper function
class TestSplitPsmsByOrganism:
    @pytest.fixture()
    def combined_target(self, tmp_path):
        path = tmp_path / 'synthetic.tide-search.target.txt'
        _write_combined_psm(path, [PSM_ROW_EUK, PSM_ROW_PRO, PSM_ROW_CONT])
        return path

    @pytest.fixture()
    def combined_decoy(self, tmp_path):
        path = tmp_path / 'synthetic.tide-search.decoy.txt'
        _write_combined_psm(path, [PSM_ROW_EUK])
        return path

    def test_returns_true_on_success(self, combined_target, combined_decoy, tmp_path):
        result = _splitPsmsByOrganism(
            target_file=combined_target,
            decoy_file=combined_decoy,
            organism_tags=ORGANISM_TAGS,
            out_dir=tmp_path,
            fileroot='synthetic',
            shared_policy='drop',
        )
        assert result is True

    def test_creates_per_organism_target_files(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        assert (tmp_path / 'EUK' / 'synthetic.EUK.tide-search.target.txt').exists()
        assert (tmp_path / 'PRO' / 'synthetic.PRO.tide-search.target.txt').exists()

    def test_creates_per_organism_decoy_files(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        assert (tmp_path / 'EUK' / 'synthetic.EUK.tide-search.decoy.txt').exists()

    def test_euk_file_contains_only_euk_rows(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        content = (tmp_path / 'EUK' / 'synthetic.EUK.tide-search.target.txt').read_text()
        assert 'TESTEUK' in content
        assert 'TESTPRO' not in content

    def test_pro_file_contains_only_pro_rows(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        content = (tmp_path / 'PRO' / 'synthetic.PRO.tide-search.target.txt').read_text()
        assert 'TESTPRO' in content
        assert 'TESTEUK' not in content

    def test_contaminant_rows_go_to_contaminants_bucket(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        cont_file = tmp_path / 'contaminants' / 'synthetic.contaminants.tide-search.target.txt'
        assert cont_file.exists()
        assert 'CONT' in cont_file.read_text()

    def test_header_is_preserved_in_each_output_file(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        for label in ('EUK', 'PRO'):
            content = (tmp_path / label / f'synthetic.{label}.tide-search.target.txt').read_text()
            assert content.startswith('scan\t')

    def test_returns_bool_when_target_file_missing(self, tmp_path):
        missing = tmp_path / 'nonexistent.percolator.target.psms.txt'
        decoy = tmp_path / 'nonexistent.percolator.decoy.psms.txt'
        result = _splitPsmsByOrganism(missing, decoy, ORGANISM_TAGS, tmp_path, 'nonexistent', 'drop')
        assert isinstance(result, bool)

    def test_skips_decoy_file_gracefully_when_absent(self, combined_target, tmp_path):
        missing_decoy = tmp_path / 'synthetic.percolator.decoy.psms.txt'
        result = _splitPsmsByOrganism(
            target_file=combined_target,
            decoy_file=missing_decoy,
            organism_tags=ORGANISM_TAGS,
            out_dir=tmp_path,
            fileroot='synthetic',
            shared_policy='drop',
        )
        assert result is True
        assert (tmp_path / 'EUK' / 'synthetic.EUK.tide-search.target.txt').exists()

    def test_output_files_are_non_empty(self, combined_target, combined_decoy, tmp_path):
        _splitPsmsByOrganism(combined_target, combined_decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        for label in ('EUK', 'PRO'):
            path = tmp_path / label / f'synthetic.{label}.tide-search.target.txt'
            assert path.stat().st_size > 0

    def test_shared_policy_drop_excludes_shared_psms(self, tmp_path):
        # A row whose protein ID contains both organism tags
        shared_row = 'syn_s\t1.0\t0.001\t0.001\tK.PEP.K\tsp|FUSION|TESTEUK_TESTPRO\n'
        target = tmp_path / 'synthetic.percolator.target.psms.txt'
        _write_combined_psm(target, [shared_row])
        decoy = tmp_path / 'synthetic.percolator.decoy.psms.txt'
        decoy.write_text(PSM_HEADER)
        _splitPsmsByOrganism(target, decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'drop')
        for label in ('EUK', 'PRO'):
            f = tmp_path / label / f'synthetic.{label}.tide-search.target.txt'
            if f.exists():
                assert 'TESTEUK_TESTPRO' not in f.read_text()

    def test_shared_policy_include_duplicates_shared_psms(self, tmp_path):
        shared_row = 'syn_s\t1.0\t0.001\t0.001\tK.PEP.K\tsp|FUSION|TESTEUK_TESTPRO\n'
        target = tmp_path / 'synthetic.percolator.target.psms.txt'
        _write_combined_psm(target, [shared_row])
        decoy = tmp_path / 'synthetic.percolator.decoy.psms.txt'
        decoy.write_text(PSM_HEADER)
        _splitPsmsByOrganism(target, decoy, ORGANISM_TAGS, tmp_path, 'synthetic', 'include')
        for label in ('EUK', 'PRO'):
            f = tmp_path / label / f'synthetic.{label}.tide-search.target.txt'
            if f.exists():
                assert 'TESTEUK_TESTPRO' in f.read_text()