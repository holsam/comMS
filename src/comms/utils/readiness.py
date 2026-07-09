'''
comMS command-readiness logic (for the experiment GUI)
'''

COMMANDS = ['convert', 'index', 'search', 'rescore', 'lfq', 'quantify', 'report', 'pipeline']

# -- missing_requirements: returns inputs still required to run the command (returned per command)
def missing_requirements(
    *,
    has_data,
    has_database,
    has_sample_sheet,
    has_organism_prefix,
    multispecies,
    has_organism_tags,
    has_trfp,
    has_crux,
    has_r_deps,
) -> dict[str, list[str]]:
    '''Return, per command, the human-readable inputs still missing to run it.'''
    base = {
        'convert': [('data files', has_data), ('ThermoRawFileParser', has_trfp)],
        'index': [('database', has_database), ('Crux', has_crux)],
        'search': [('data files', has_data), ('database', has_database), ('Crux', has_crux)],
        'rescore': [('database', has_database)] + [('organism patterns', has_organism_tags)] + [('Crux', has_crux)],
        'lfq': [('sample sheet', has_sample_sheet), ('data files', has_data), ('Crux', has_crux)],
        'quantify': [('database', has_database), ('Crux', has_crux)],
        'report': [('sample sheet', has_sample_sheet), ('organism prefix', has_organism_prefix), ('R dependencies', has_r_deps)],
    }
    base['pipeline'] = [item for items in base.values() for item in items]
    return {cmd: [name for name, ok in items if not ok] for cmd, items in base.items()}