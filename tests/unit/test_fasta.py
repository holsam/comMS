'''
Unit tests for src/comms/utils/fasta.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import internal functions under test
from comms.utils.fasta import readFasta, writeFasta, _searchHeaderForTag, splitFastaByOrganism

# -- Define shared fixtures for unit tests
@pytest.fixture()
def single_entry_fasta(tmp_path):
    p = tmp_path / 'single.fasta'
    p.write_text('>sp|TE001|GENE1_TESTEUK Protein one\nACDEFGHIK\n')
    return p

@pytest.fixture()
def multi_entry_fasta(tmp_path):
    p = tmp_path / 'multi.fasta'
    p.write_text(
        '>sp|TE001|GENE1_TESTEUK Protein one\nACDEFGHIK\n'
        '>sp|TP001|GENE1_TESTPRO Protein two\nSAMPLEK\n'
        '>cRAP|TC001|TESTCON001 Contaminant one\nPEPTIDEFK\n'
    )
    return p

@pytest.fixture()
def wrapped_sequence_fasta(tmp_path):
    p = tmp_path / 'wrapped.fasta'
    p.write_text('>sp|TE001|GENE1_TESTEUK Protein one\nACDEF\nGHIK\nLMNPQR\n')
    return p

@pytest.fixture()
def empty_sequence_fasta(tmp_path):
    p = tmp_path / 'empty_seq.fasta'
    p.write_text('>sp|TE001|GENE1_TESTEUK Protein one\n')
    return p

@pytest.fixture()
def two_organism_tags():
    return {'EUK': 'TESTEUK', 'PRO': 'TESTPRO'}

@pytest.fixture()
def combined_fasta(tmp_path):
    p = tmp_path / 'combined.fasta'
    p.write_text(
        '>sp|TE001|GENE1_TESTEUK Protein one\nACDEFGHIK\n'
        '>sp|TE002|GENE2_TESTEUK Protein two\nLMNPQR\n'
        '>sp|TP001|GENE1_TESTPRO Protein three\nSAMPLEK\n'
        '>cRAP|TC001|TESTCON001 Contaminant one\nPEPTIDEFK\n'
    )
    return p

@pytest.fixture()
def no_contaminant_fasta(tmp_path):
    p = tmp_path / 'no_contaminants.fasta'
    p.write_text(
        '>sp|TE001|GENE1_TESTEUK Protein one\nACDEFGHIK\n'
        '>sp|TP001|GENE1_TESTPRO Protein two\nSAMPLEK\n'
    )
    return p

# -- Define unit test for readFasta function
class TestReadFasta:
    def test_returns_list(self, single_entry_fasta):
        result = readFasta(single_entry_fasta)
        assert isinstance(result, list)
    
    def test_single_entry_returns_one_item(self, single_entry_fasta):
        result = readFasta(single_entry_fasta)
        assert len(result) == 1

    def test_multi_entry_returns_correct_count(self, multi_entry_fasta):
        result = readFasta(multi_entry_fasta)
        assert len(result) == 3

    def test_entry_is_list_of_two(self, single_entry_fasta):
        result = readFasta(single_entry_fasta)
        assert isinstance(result[0], list)
        assert len(result[0]) == 2

    def test_header_does_not_contain_separator(self, single_entry_fasta):
        result = readFasta(single_entry_fasta)
        assert not result[0][0].startswith('>')

    def test_header_content_is_correct(self, single_entry_fasta):
        result = readFasta(single_entry_fasta)
        assert result[0][0] == 'sp|TE001|GENE1_TESTEUK Protein one'

    def test_sequence_content_is_correct(self, single_entry_fasta):
        result = readFasta(single_entry_fasta)
        assert result[0][1] == 'ACDEFGHIK'

    def test_wrapped_sequence_is_joined(self, wrapped_sequence_fasta):
        result = readFasta(wrapped_sequence_fasta)
        assert result[0][1] == 'ACDEFGHIKLMNPQR'

    def test_wrapped_sequence_contains_no_newlines(self, wrapped_sequence_fasta):
        result = readFasta(wrapped_sequence_fasta)
        assert '\n' not in result[0][1]

    def test_empty_sequence_returns_empty_string(self, empty_sequence_fasta):
        result = readFasta(empty_sequence_fasta)
        assert result[0][1] == ''

    def test_multi_entry_order_preserved(self, multi_entry_fasta):
        result = readFasta(multi_entry_fasta)
        assert result[0][0].startswith('sp|TE001')
        assert result[1][0].startswith('sp|TP001')
        assert result[2][0].startswith('cRAP|TC001')

# -- Define unit tests for writeFasta function
class TestWriteFasta:
    def test_creates_file(self, tmp_path):
        out = tmp_path / 'out.fasta'
        writeFasta([['HEADER', 'ACDEFGHIK']], out)
        assert out.exists()

    def test_header_prefixed_with_separator(self, tmp_path):
        out = tmp_path / 'out.fasta'
        writeFasta([['HEADER', 'ACDEFGHIK']], out)
        lines = out.read_text().splitlines()
        assert lines[0] == '>HEADER'

    def test_sequence_on_separate_line(self, tmp_path):
        out = tmp_path / 'out.fasta'
        writeFasta([['HEADER', 'ACDEFGHIK']], out)
        lines = out.read_text().splitlines()
        assert lines[1] == 'ACDEFGHIK'

    def test_multi_entry_all_present(self, tmp_path):
        out = tmp_path / 'out.fasta'
        data = [['HDR1', 'AAAA'], ['HDR2', 'CCCC'], ['HDR3', 'GGGG']]
        writeFasta(data, out)
        text = out.read_text()
        assert '>HDR1' in text
        assert '>HDR2' in text
        assert '>HDR3' in text

    def test_round_trip_via_read_fasta(self, multi_entry_fasta, tmp_path):
        original = readFasta(multi_entry_fasta)
        out = tmp_path / 'written.fasta'
        writeFasta(original, out)
        reloaded = readFasta(out)
        assert original == reloaded

# -- Define unit tests for _searchHeaderForTag helper function
class TestSearchHeaderForTag:
    def test_returns_true_on_match(self, two_organism_tags):
        entry = ['sp|TE001|GENE1_TESTEUK Protein one', 'ACDEFGHIK']
        subfastas = {}
        result = _searchHeaderForTag(subfastas, two_organism_tags, entry)
        assert result is True

    def test_returns_false_on_no_match(self, two_organism_tags):
        entry = ['cRAP|TC001|TESTCON001 Contaminant', 'PEPTIDEFK']
        subfastas = {}
        result = _searchHeaderForTag(subfastas, two_organism_tags, entry)
        assert result is False

    def test_adds_entry_to_correct_key(self, two_organism_tags):
        entry = ['sp|TE001|GENE1_TESTEUK Protein one', 'ACDEFGHIK']
        subfastas = {}
        _searchHeaderForTag(subfastas, two_organism_tags, entry)
        assert 'EUK' in subfastas
        assert entry in subfastas['EUK']

    def test_creates_key_on_first_match(self, two_organism_tags):
        entry = ['sp|TP001|GENE1_TESTPRO Protein two', 'SAMPLEK']
        subfastas = {}
        _searchHeaderForTag(subfastas, two_organism_tags, entry)
        assert 'PRO' in subfastas

    def test_appends_to_existing_key(self, two_organism_tags):
        entry1 = ['sp|TE001|GENE1_TESTEUK Protein one', 'ACDEFGHIK']
        entry2 = ['sp|TE002|GENE2_TESTEUK Protein two', 'LMNPQR']
        subfastas = {}
        _searchHeaderForTag(subfastas, two_organism_tags, entry1)
        _searchHeaderForTag(subfastas, two_organism_tags, entry2)
        assert len(subfastas['EUK']) == 2

    def test_does_not_add_non_matching_entry(self, two_organism_tags):
        entry = ['cRAP|TC001|TESTCON001 Contaminant', 'PEPTIDEFK']
        subfastas = {}
        _searchHeaderForTag(subfastas, two_organism_tags, entry)
        assert subfastas == {}

    def test_uses_regex_not_plain_substring(self):
        '''A tag anchored to end of string should not match a longer header.'''
        tags = {'EUK': 'TESTEUK$'}
        entry_match = ['sp|TE001|GENE1_TESTEUK', 'ACDEFGHIK']
        entry_no_match = ['sp|TE002|GENE1_NOTTESTEUK extra', 'LMNPQR']
        subfastas = {}
        assert _searchHeaderForTag(subfastas, tags, entry_match) is True
        subfastas = {}
        assert _searchHeaderForTag(subfastas, tags, entry_no_match) is False

    def test_assigns_to_first_matching_tag_only(self):
        '''An entry matching two tags is assigned only to the first.'''
        tags = {'EUK': 'TESTEUK', 'Also': 'TE001'}
        entry = ['sp|TE001|GENE1_TESTEUK Protein one', 'ACDEFGHIK']
        subfastas = {}
        _searchHeaderForTag(subfastas, tags, entry)
        assert 'EUK' in subfastas
        assert 'Also' not in subfastas

# -- Define unit tests for SplitFastaByOrganism function
class TestSplitFastaByOrganism:
    def test_returns_dict(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        assert isinstance(result, dict)

    def test_returns_one_key_per_organism(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        assert set(result.keys()) == {'EUK', 'PRO'}

    def test_contaminants_key_absent_from_return(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        assert 'contaminants' not in result

    def test_returns_paths(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        for v in result.values():
            assert isinstance(v, Path)

    def test_output_files_exist(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        for path in result.values():
            assert path.exists()

    def test_output_files_use_fa_extension(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        for path in result.values():
            assert path.suffix == '.fa'

    def test_output_files_named_by_label(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        assert result['EUK'].name == 'EUK.fa'
        assert result['PRO'].name == 'PRO.fa'

    def test_subfasta_contains_only_organism_proteins(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        for subfasta in result.keys():
            file_entries = readFasta(result[subfasta])
            headers = [e[0] for e in file_entries]
            if subfasta == 'EUK':
                assert any('TESTEUK' in h for h in headers)
                assert not any('TESTPRO' in h for h in headers)
            if subfasta == 'PRO':
                assert any('TESTPRO' in h for h in headers)
                assert not any('TESTEUK' in h for h in headers)

    def test_contaminant_appended_to_all_organism_subfastas(self, combined_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(combined_fasta, tmp_path, two_organism_tags)
        for label, path in result.items():
            entries = readFasta(path)
            headers = [e[0] for e in entries]
            assert any('TESTCON001' in h for h in headers), (
                f'Contaminant not found in {label} sub-FASTA'
            )

    def test_no_crash_when_no_contaminants(self, no_contaminant_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(no_contaminant_fasta, tmp_path, two_organism_tags)
        assert set(result.keys()) == {'EUK', 'PRO'}

    def test_no_contaminant_subfastas_contain_only_organism_proteins(self, no_contaminant_fasta, two_organism_tags, tmp_path):
        result = splitFastaByOrganism(no_contaminant_fasta, tmp_path, two_organism_tags)
        mt_entries = readFasta(result['EUK'])
        assert all('TESTEUK' in e[0] for e in mt_entries)

    def test_empty_fasta_returns_empty_dict(self, tmp_path):
        empty = tmp_path / 'empty.fasta'
        empty.write_text('')
        result = splitFastaByOrganism(empty, tmp_path, {'EUK': 'TESTEUK'})
        assert result == {}