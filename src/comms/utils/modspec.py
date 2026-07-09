'''
comMS shared modification-spec and organism helpers

Used by commands/config.py (persisting changes to a config file) and commands/index.py
(applying one-off, non-persisted overrides for a single `comms index` run). Every
function here is pure — it takes a value in and returns a new value out.
'''

# -- Import external dependencies
import re

# -- Import internal functions
from comms.utils.log import logMsg

# -- Modification constants
CARBAMIDOMETHYL_MOD = 'C+57.0215'    # static carbamidomethylation of Cys
MET_OX_MOD = '1M+15.9949'    # variable Met oxidation
PHOSPHO_MOD = '1STY+79.966331'    # variable STY phosphorylation
NCYC_MOD = '1Q-17.027'    # N-terminal Gln cyclisation
NACE_MOD = '1X+42.011'    # N-terminal protein acetylation
MANAGED_MOD_PATTERNS: dict[str, str] = {
    r'^\d*C[+\-]': '--iodo / --no-iodo',
    r'^\d*M\+15\.9949': '--ox / --no-ox',
    r'^\d*STY\+79\.966331': '--phos / --no-phos',
}    # mods that --custom is not allowed to duplicate (maps the residue/pattern that identifies each managed mod to its flag name)

# -- Resolution constants
MZ_BIN_WIDTH_HIGH_RES = 0.02    # high-resolution instruments (default)
MZ_BIN_WIDTH_LOW_RES = 1.0005079    # low-resolution instruments
SCORE_FUNC_HIGH_RES = 'xcorr'    # high-resolution instruments (default)
SCORE_FUNC_LOW_RES = 'combined-p-value'    # low-resolution instruments

# -- apply_mod: returns mods_spec string
def apply_mod(mods_spec: str, mod: str, exclusive_pattern: str | None = None) -> str:
    '''
    Add or remove a mod entry in a Tide mods_spec string.
    '''
    entries = [e.strip() for e in mods_spec.split(',') if e.strip()]
    if exclusive_pattern:
        pattern = re.compile(exclusive_pattern, re.IGNORECASE)
        entries = [e for e in entries if not pattern.match(e)]
    elif mod == '':
        pass
    else:
        entries = [e for e in entries if e != mod]
    if mod:
        entries = [mod] + entries
    return ','.join(entries)

# -- apply_iodo: returns fixed_mods string
def apply_iodo(fixed_mods: str, iodo: bool) -> str:
    '''
    Add or remove the carbamidomethylation Cys mod in a Tide fixed_mods string
    '''
    entries = [e.strip() for e in fixed_mods.split(',') if e.strip()]
    entries = [e for e in entries if e != CARBAMIDOMETHYL_MOD and e != 'C+0']
    if iodo:
        entries = [CARBAMIDOMETHYL_MOD] + entries
    else:
        entries = ['C+0'] + entries    # Crux automatically adds cysteine carbamidomethylation unless this string present
    return ','.join(entries)

# -- apply_custom_mod: returns custom_mods string
def apply_custom_mod(custom_mods: str, new_entry: str) -> str:
    '''
    Add a custom mod entry to the custom_mods string, or clear all custom mods if new_entry is an empty string
    '''
    if new_entry == '':
        return ''
    for pattern, flag_name in MANAGED_MOD_PATTERNS.items():
        if re.match(pattern, new_entry, re.IGNORECASE):
            logMsg.warn(f'{new_entry} is managed by the {flag_name} flag, ignoring')
            return custom_mods
    entries = [e.strip() for e in custom_mods.split(',') if e.strip()]
    if new_entry not in entries:
        entries.append(new_entry)
    out_str = ','.join(entries)
    logMsg.debug(f'custom_mods updated: {out_str}')
    return out_str

# -- apply_organism: returns config dict with organism section replaced
def apply_organism(cfg: dict, organism: dict[str, str]) -> dict:
    '''
    Replace the [organism] section of a config dict with the supplied dictionary.
    '''
    cfg['organism'] = organism
    logMsg.debug(f'organism section set to {organism}')
    return cfg

# -- parse_organism_arg: returns dict parsed from list of 'Key=Pattern' strings
def parse_organism_arg(pairs: list[str]) -> dict[str, str]:
    '''
    Parse a list of 'Label=Pattern' strings into a dict.
    '''
    result = {}
    for item in pairs:
        if '=' not in item:
            logMsg.error(f'Invalid organism argument {item} (expected format: Organism=Pattern)')
            raise SystemExit(1)
        key, _, pattern = item.partition('=')
        key = ''.join(key.split())
        pattern = ''.join(pattern.split())
        if not key:
            logMsg.error(f'Empty label in organism argument: {item}')
            raise SystemExit(1)
        if not pattern:
            logMsg.error(f'Empty pattern in organism argument: {item}')
            raise SystemExit(1)
        result[key] = pattern
    return result

# -- apply_protocol_flags: returns a config dict with protocol-level flags applied
def apply_protocol_flags(
    cfg: dict,
    *,
    iodo: bool | None = None,
    ox: bool | None = None,
    phos: bool | None = None,
    n_cyc: bool | None = None,
    n_ace: bool | None = None,
    clip_met: bool | None = None,
    low_res: bool | None = None,
    missed_cleavages: int | None = None,
) -> dict:
    '''
    Apply protocol flags to a config dictionary and return it
        iodo — owns the Cys slot in index.fixed_mods exclusively
        ox — adds/removes 1M+15.9949 in index.mods_spec
        phos — adds/removes 1STY+79.966331 in index.mods_spec
        n_cyc — adds/removes 1Q-17.027 in index.nterm_peptide_mods_spec
        n_ace — adds/removes 1X+42.011 in index.nterm_protein_mods_spec
        low_res — sets search.mz_bin_width and search.score_function
        missed_cleavages — sets index.missed_cleavages directly
    '''
    cfg.setdefault('search', {})
    cfg.setdefault('index', {})
    cfg['index'].setdefault('fixed_mods', '')
    cfg['index'].setdefault('nterm_peptide_mods_spec', '')
    cfg['index'].setdefault('nterm_protein_mods_spec', '')
    if iodo is not None:
        cfg['index']['fixed_mods'] = apply_iodo(cfg['index'].get('fixed_mods', ''), iodo=iodo)
        logMsg.debug(f'{"--iodo" if iodo else "--no-iodo"} applied: fixed_mods updated to {cfg["index"]["fixed_mods"]}')
    if ox is not None:
        spec = cfg['index'].get('mods_spec', '')
        if ox:
            cfg['index']['mods_spec'] = apply_mod(spec, mod=MET_OX_MOD)
        else:
            cfg['index']['mods_spec'] = apply_mod(spec, mod='', exclusive_pattern=r'^\d*M\+15\.9949')
        logMsg.debug(f'{"--ox" if ox else "--no-ox"} applied: mods_spec updated to {cfg["index"]["mods_spec"]}')
    if phos is not None:
        spec = cfg['index'].get('mods_spec', '')
        if phos:
            cfg['index']['mods_spec'] = apply_mod(spec, mod=PHOSPHO_MOD)
        else:
            cfg['index']['mods_spec'] = apply_mod(spec, mod='', exclusive_pattern=r'^\d*STY\+79\.966331')
        logMsg.debug(f'{"--phos" if phos else "--no-phos"} applied: mods_spec updated to {cfg["index"]["mods_spec"]}')
    if n_cyc is not None:
        spec = cfg['index'].get('nterm_peptide_mods_spec', '')
        if n_cyc:
            cfg['index']['nterm_peptide_mods_spec'] = apply_mod(spec, mod=NCYC_MOD)
        else:
            cfg['index']['nterm_peptide_mods_spec'] = apply_mod(spec, mod='', exclusive_pattern=r'^\d*Q\-17\.027')
        logMsg.debug(f'{"--n-cyc" if n_cyc else "--no-n-cyc"} applied: nterm_peptide_mods_spec updated to {cfg["index"]["nterm_peptide_mods_spec"]}')
    if n_ace is not None:
        spec = cfg['index'].get('nterm_protein_mods_spec', '')
        if n_ace:
            cfg['index']['nterm_protein_mods_spec'] = apply_mod(spec, mod=NACE_MOD)
        else:
            cfg['index']['nterm_protein_mods_spec'] = apply_mod(spec, mod='', exclusive_pattern=r'^\d*X\+42\.011')
        logMsg.debug(f'{"--n-ace" if n_ace else "--no-n-ace"} applied: nterm_protein_mods_spec updated to {cfg["index"]["nterm_protein_mods_spec"]}')
    if low_res is not None:
        cfg['search']['mz_bin_width'] = MZ_BIN_WIDTH_LOW_RES if low_res else MZ_BIN_WIDTH_HIGH_RES
        cfg['search']['score_function'] = SCORE_FUNC_LOW_RES if low_res else SCORE_FUNC_HIGH_RES
        logMsg.debug(f'{"--low-res" if low_res else "--high-res"} applied: mz_bin_width: {cfg["search"]["mz_bin_width"]}, score_function: {cfg["search"]["score_function"]}')
    if clip_met is not None:
        cfg['index']['clip_n_met'] = bool(clip_met)
        logMsg.debug(f'{"--clip-met" if clip_met else "--no-clip-met"} applied: {cfg["index"]["clip_n_met"]}')
    if missed_cleavages is not None:
        cfg['index']['missed_cleavages'] = missed_cleavages
        logMsg.debug(f'--missed-cleavages applied: {missed_cleavages}')
    return cfg