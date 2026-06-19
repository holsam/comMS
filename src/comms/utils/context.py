'''
comMS experiment context resolution
'''

# -- Import external dependencies
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import resolveConfig

# -- _normalise_dirs: return (root, comms_dir)
def _normalise_dirs(experiment_dir: Path) -> tuple[Path, Path]:
    '''
    Return the experiment root (where outputs go, as <root>/comms/results/...) and its comms/ directory (which holds experiment.toml, config.toml and the
    sample sheet); if the user points at the comms/ directory itself, the root is as its parent so outputs are not nested as comms/comms/
    '''
    if experiment_dir.name == 'comms':
        return experiment_dir.parent, experiment_dir
    if (experiment_dir / 'experiment.toml').exists():
        # i.e. pointed at a comms/ dir that's been renamed
        return experiment_dir.parent, experiment_dir
    return experiment_dir, experiment_dir / 'comms'

# -- Define dataclass ExperimentContext to hold a resolved view of an experiment directory
@dataclass
class ExperimentContext:
    root: Path
    comms_dir: Path
    config: dict
    config_source: str
    bin_dir: Optional[Path]
    metadata: dict = field(default_factory=dict)
    # -- stored external inputs (experiment.toml [files] / [report]) --
    def _file(self, key: str) -> Optional[Path]:
        value = self.metadata.get('files', {}).get(key)
        return Path(value) if value else None

    @property
    def data_files(self) -> list[Path]:
        '''Source data files (RAW/mzML) recorded in experiment.toml'''
        return [Path(p) for p in self.metadata.get('files', {}).get('data', [])]

    @property
    def database(self) -> Optional[Path]:
        return self._file('database')

    @property
    def sample_sheet(self) -> Optional[Path]:
        return self._file('sample_sheet')

    @property
    def analysis_mode(self) -> Optional[str]:
        value = self.metadata.get('experiment', {}).get('analysis')
        return str(value) if value else None
    
    @property
    def multispecies(self) -> bool:
        if self.analysis_mode == 'multi':
            return True
        if self.analysis_mode == 'single':
            return False
        # Fall back to infer from config
        return bool(self.config.get('organism'))

    @property
    def organism_prefix(self) -> Optional[str]:
        return self.metadata.get('report', {}).get('organism_prefix')

    @property
    def ref_info(self) -> Optional[Path]:
        v = self.metadata.get('report', {}).get('ref_info')
        return Path(v) if v else None

    @property
    def cont_csv(self) -> Optional[Path]:
        v = self.metadata.get('report', {}).get('cont_csv')
        return Path(v) if v else None

    # Define class method resolve to resolve the various class attributes
    @classmethod
    def resolve(self, experiment_dir: Path) -> 'ExperimentContext':
        root, comms_dir = _normalise_dirs(experiment_dir)
        metadata: dict = {}
        meta_path = comms_dir / 'experiment.toml'
        if meta_path.exists():
            with meta_path.open('rb') as f:
                metadata = tomllib.load(f)
            logMsg.debug(f'Loaded experiment metadata from {meta_path}')
        else:
            logMsg.debug(f'No experiment.toml at {meta_path}; using fallback resolution')
        # Resolve configuration file
        config, source = resolveConfig(comms_dir)
        # Resolve bin directory
        bin_dir: Optional[Path] = None
        exp_bin = metadata.get('experiment', {}).get('bin_dir')
        if exp_bin:
            bin_dir = Path(exp_bin)
            logMsg.debug(f'Bin directory from experiment.toml: {bin_dir}')
        # Return attributes
        return self(
            root=root,
            comms_dir=comms_dir,
            config=config,
            config_source=source,
            bin_dir=bin_dir,
            metadata=metadata,
        )

# -- results_dir: return path of the canonical output directory for a command
def results_dir(ctx: ExperimentContext, command: str) -> Path:
    return ctx.root / 'comms' / 'results' / command

# -- _choose: return a Path after handling overrides
def _choose(stored, override, label: str, *, must_exist: bool = True) -> Path:
    if override is not None:
        if stored is not None and Path(override) != Path(stored):
            logMsg.warn(f'{label}: command-line value overrides experiment value ({stored})')
        chosen = Path(override)
    elif stored is not None:
        chosen = Path(stored)
    else:
        logMsg.error(f'No {label} supplied and none found in the experiment context. Set one with comms experiment, or pass it on the command line.')
        raise SystemExit(1)
    if must_exist and not chosen.exists():
        logMsg.error(f'{label} not found: {chosen}')
        raise SystemExit(1)
    return chosen

# -- _check_files: return a list of Paths after checking they exist
def _check_files(files, label: str) -> list[Path]:
    out = [Path(f) for f in files]
    for f in out:
        if not f.exists():
            logMsg.error(f'{label} not found: {f}')
            raise SystemExit(1)
    return out

# -- resolve_results_input: return a Path to a prior stage's output directory
def resolve_results_input(ctx, command, override=None, *, must_exist=True) -> Path:
    return _choose(results_dir(ctx, command), override, f'{command} directory', must_exist=must_exist)

# -- resolve_data_files: return a list of Paths to data files from -d/--data or [files].data
def resolve_data_files(ctx, override=None) -> list[Path]:
    stored = ctx.data_files
    if override:
        chosen = [Path(f) for f in override]
        if stored and set(chosen) != set(stored):
            logMsg.warn('data files: command-line --data overrides the experiment data list')
    elif stored:
        chosen = stored
    else:
        logMsg.error('No data files supplied and none found in the experiment context. Add files with comms experiment, or pass them with --data.')
        raise SystemExit(1)
    return _check_files(chosen, 'data file')

# -- resolve_mzml_files: returns list of Paths for .mzML to search (explicit override, else convert results)
def resolve_mzml_files(ctx, override=None) -> list[Path]:
    if override:
        return _check_files(override, 'mzML data file')
    conv = results_dir(ctx, 'convert')
    files = sorted(conv.glob('[!.]*.mzML')) + sorted(conv.glob('[!.]*.mzML.gz'))
    if not files:
        logMsg.error(f'No .mzML files found in {conv}. Run comms convert, or pass files with --data.')
        raise SystemExit(1)
    return files

# -- resolve_database: returns a Path to FASTA database
def resolve_database(ctx, override=None) -> Path:
    return _choose(ctx.database, override, 'database')

# -- resolve_sample_sheet: returns a Path to sample sheet
def resolve_sample_sheet(ctx, override=None) -> Path:
    return _choose(ctx.sample_sheet, override, 'sample sheet')


# -- resolve_organism_prefix: returns a string for report's primary-organism prefix
def resolve_organism_prefix(ctx, override=None) -> str:
    if override is not None:
        if ctx.organism_prefix and override != ctx.organism_prefix:
            logMsg.warn(f'organism prefix: command-line value overrides experiment value ({ctx.organism_prefix})')
        return override
    if ctx.organism_prefix:
        return ctx.organism_prefix
    logMsg.error('No organism prefix supplied and none found in the experiment context.')
    raise SystemExit(1)