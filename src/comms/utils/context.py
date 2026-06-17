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