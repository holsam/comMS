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
    has_organism_tags
) -> dict[str, list[str]]:
    '''Return, per command, the human-readable inputs still missing to run it.'''
    base = {
        'convert': [('data files', has_data)],
        'index': [('database', has_database)],
        'search': [('data files', has_data), ('database', has_database)],
        'rescore': [('database', has_database)] + [('organism patterns', has_organism_tags)],
        'lfq': [('sample sheet', has_sample_sheet), ('data files', has_data)],
        'quantify': [('database', has_database)],
        'report': [('sample sheet', has_sample_sheet), ('organism prefix', has_organism_prefix)],
    }
    base['pipeline'] = [item for items in base.values() for item in items]
    return {cmd: [name for name, ok in items if not ok] for cmd, items in base.items()}