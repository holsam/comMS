'''
Unit tests for src/comms/utils/modspec.py
'''
import pytest

from comms.utils.modspec import (
    CARBAMIDOMETHYL_MOD, MET_OX_MOD, PHOSPHO_MOD, NCYC_MOD, NACE_MOD,
    MANAGED_MOD_PATTERNS, MZ_BIN_WIDTH_HIGH_RES, MZ_BIN_WIDTH_LOW_RES,
    SCORE_FUNC_HIGH_RES, SCORE_FUNC_LOW_RES,
    apply_mod, apply_iodo, apply_custom_mod, apply_organism,
    parse_organism_arg, apply_protocol_flags,
)


class TestApplyMod:
    def test_adds_to_empty_spec(self):
        assert apply_mod('', MET_OX_MOD) == MET_OX_MOD

    def test_adds_to_existing_spec(self):
        assert MET_OX_MOD in apply_mod('1K+28.0313', MET_OX_MOD)

    def test_prepends_new_mod(self):
        result = apply_mod('1K+28.0313', MET_OX_MOD)
        assert result.startswith(MET_OX_MOD)

    def test_duplicate_not_added_twice(self):
        result = apply_mod(MET_OX_MOD, MET_OX_MOD)
        assert result.count(MET_OX_MOD) == 1

    def test_removal_with_exclusive_pattern(self):
        result = apply_mod(MET_OX_MOD, mod='', exclusive_pattern=r'^\d*M\+15\.9949')
        assert MET_OX_MOD not in result

    def test_exclusive_pattern_replaces_on_add(self):
        result = apply_mod('1M+999.0', MET_OX_MOD, exclusive_pattern=r'^\d*M\+')
        assert '1M+999.0' not in result
        assert MET_OX_MOD in result

    def test_no_leading_or_trailing_commas(self):
        result = apply_mod('', MET_OX_MOD)
        assert not result.startswith(',') and not result.endswith(',')

    def test_removal_of_absent_mod_is_noop(self):
        assert apply_mod('1K+28.0313', mod='', exclusive_pattern=r'^\d*M\+15\.9949') == '1K+28.0313'


class TestApplyIodo:
    def test_adds_carbamidomethyl(self):
        assert CARBAMIDOMETHYL_MOD in apply_iodo('', iodo=True)

    def test_removes_carbamidomethyl(self):
        assert CARBAMIDOMETHYL_MOD not in apply_iodo(CARBAMIDOMETHYL_MOD, iodo=False)

    def test_no_iodo_adds_c_plus_0(self):
        assert 'C+0' in apply_iodo('', iodo=False)

    def test_idempotent(self):
        result = apply_iodo(apply_iodo('', iodo=True), iodo=True)
        assert result.count(CARBAMIDOMETHYL_MOD) == 1


class TestApplyCustomMod:
    def test_adds_entry_to_empty(self):
        assert apply_custom_mod('', '1K+28.0313') == '1K+28.0313'

    def test_empty_string_clears_all(self):
        assert apply_custom_mod('1K+28.0313', '') == ''

    def test_duplicate_not_added(self):
        once = apply_custom_mod('', '1K+28.0313')
        twice = apply_custom_mod(once, '1K+28.0313')
        assert twice.count('1K+28.0313') == 1

    @pytest.mark.parametrize('managed_entry', ['1M+15.9949', 'C+57.0215', '1STY+79.966331'])
    def test_managed_mod_rejected(self, managed_entry):
        assert apply_custom_mod('', managed_entry) == ''

    def test_managed_mod_patterns_is_dict_of_pattern_to_flag(self):
        assert isinstance(MANAGED_MOD_PATTERNS, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in MANAGED_MOD_PATTERNS.items())


class TestApplyOrganism:
    def test_sets_organism_section(self):
        cfg = apply_organism({}, {'Mt': 'MEDTR'})
        assert cfg['organism'] == {'Mt': 'MEDTR'}

    def test_replaces_existing(self):
        cfg = apply_organism({'organism': {'Old': 'X'}}, {'New': 'Y'})
        assert cfg['organism'] == {'New': 'Y'}

    def test_does_not_touch_other_sections(self):
        cfg = apply_organism({'search': {'threads': 4}}, {'Mt': 'MEDTR'})
        assert cfg['search'] == {'threads': 4}


class TestParseOrganismArg:
    def test_single_pair(self):
        assert parse_organism_arg(['Mt=MEDTR']) == {'Mt': 'MEDTR'}

    def test_multiple_pairs(self):
        assert parse_organism_arg(['Mt=MEDTR', 'Ri=RHIIR']) == {'Mt': 'MEDTR', 'Ri': 'RHIIR'}

    def test_strips_whitespace(self):
        assert parse_organism_arg([' Mt = MEDTR ']) == {'Mt': 'MEDTR'}

    def test_raises_on_missing_equals(self):
        with pytest.raises(SystemExit):
            parse_organism_arg(['MtMEDTR'])

    def test_raises_on_empty_key(self):
        with pytest.raises(SystemExit):
            parse_organism_arg(['=MEDTR'])

    def test_raises_on_empty_pattern(self):
        with pytest.raises(SystemExit):
            parse_organism_arg(['Mt='])

    def test_empty_list_returns_empty_dict(self):
        assert parse_organism_arg([]) == {}


class TestApplyProtocolFlags:
    def test_low_res_sets_bin_width_and_score(self):
        cfg = apply_protocol_flags({}, low_res=True)
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_high_res_sets_bin_width_and_score(self):
        cfg = apply_protocol_flags({}, low_res=False)
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_none_flags_are_noop(self):
        cfg = apply_protocol_flags({'search': {'threads': 4}})
        assert cfg['search']['threads'] == 4

    # -- new: clip_met --
    def test_clip_met_true_sets_bool_true(self):
        cfg = apply_protocol_flags({}, clip_met=True)
        assert cfg['index']['clip_n_met'] is True

    def test_clip_met_false_sets_bool_false(self):
        cfg = apply_protocol_flags({}, clip_met=False)
        assert cfg['index']['clip_n_met'] is False

    def test_clip_met_stored_as_bool_not_string(self):
        '''Regression test: clip_n_met must never be persisted as a string.'''
        cfg = apply_protocol_flags({}, clip_met=True)
        assert isinstance(cfg['index']['clip_n_met'], bool)

    def test_clip_met_none_is_noop(self):
        cfg = apply_protocol_flags({'index': {}}, clip_met=None)
        assert 'clip_n_met' not in cfg['index']

    # -- new: missed_cleavages --
    def test_missed_cleavages_sets_value(self):
        cfg = apply_protocol_flags({}, missed_cleavages=3)
        assert cfg['index']['missed_cleavages'] == 3

    def test_missed_cleavages_none_is_noop(self):
        cfg = apply_protocol_flags({'index': {}}, missed_cleavages=None)
        assert 'missed_cleavages' not in cfg['index']

    def test_missed_cleavages_and_clip_met_coexist(self):
        cfg = apply_protocol_flags({}, clip_met=True, missed_cleavages=2)
        assert cfg['index']['clip_n_met'] is True
        assert cfg['index']['missed_cleavages'] == 2

    def test_mods_flags_unaffected_by_new_flags(self):
        cfg = apply_protocol_flags({}, ox=True, clip_met=True, missed_cleavages=1)
        assert MET_OX_MOD in cfg['index']['mods_spec']
        assert cfg['index']['clip_n_met'] is True