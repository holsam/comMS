'''
Unit tests for src/comms/utils/readiness.py
'''
from comms.utils.readiness import missing_requirements, COMMANDS


def _all_true(**overrides):
    base = dict(
        has_data=True, has_database=True, has_sample_sheet=True, has_organism_prefix=True,
        multispecies=True, has_organism_tags=True, has_trfp=True, has_crux=True, has_r_deps=True,
    )
    base.update(overrides)
    return base


class TestMissingRequirements:
    def test_all_satisfied_every_command_empty(self):
        result = missing_requirements(**_all_true())
        assert all(gaps == [] for gaps in result.values())

    def test_missing_data_appears_only_in_relevant_commands(self):
        result = missing_requirements(**_all_true(has_data=False))
        assert 'data files' in result['convert']
        assert 'data files' in result['search']
        assert 'data files' in result['lfq']
        assert 'data files' not in result['index']
        assert 'data files' not in result['quantify']

    def test_missing_crux_appears_in_every_crux_dependent_command(self):
        result = missing_requirements(**_all_true(has_crux=False))
        for cmd in ('index', 'search', 'rescore', 'lfq', 'quantify'):
            assert 'Crux' in result[cmd]
        assert 'Crux' not in result['convert']
        assert 'Crux' not in result['report']

    def test_missing_trfp_only_affects_convert(self):
        result = missing_requirements(**_all_true(has_trfp=False))
        assert 'ThermoRawFileParser' in result['convert']
        assert all('ThermoRawFileParser' not in gaps for cmd, gaps in result.items() if cmd != 'convert')

    def test_missing_r_deps_only_affects_report(self):
        result = missing_requirements(**_all_true(has_r_deps=False))
        assert 'R dependencies' in result['report']

    def test_pipeline_is_union_of_all_other_commands(self):
        result = missing_requirements(**_all_true(has_data=False, has_crux=False))
        expected = set()
        for cmd, gaps in result.items():
            if cmd != 'pipeline':
                expected.update(gaps)
        assert set(result['pipeline']) == expected

    # -- the §1.2 assumption, pinned explicitly --
    def test_rescore_requires_organism_patterns_only_when_multispecies(self):
        single = missing_requirements(**_all_true(multispecies=False, has_organism_tags=False))
        multi = missing_requirements(**_all_true(multispecies=True, has_organism_tags=False))
        assert 'organism patterns' not in single['rescore']
        assert 'organism patterns' in multi['rescore']