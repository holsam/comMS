'''
comMS motif extension: configuration import and defaults
'''

# -- Import external dependencies
import shutil, tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

# -- Import internal comMS logMsg class
from comms.utils.log import logMsg

# -- Define filename for configuration file
CONFIG_FILENAME = 'config_motif.toml'

# -- Define dataclass MotifConfig to hold motif configuration
@dataclass
class MotifConfig:
    raw: dict = field(default_factory=dict)

# -- _bundled_default: returns a Traversable to the bundled default motif configuration
def _bundled_default() -> 'resources.abc.Traversable':
    return resources.files('comms.ext.motif.data').joinpath('config_motif.defaults.toml')

# -- _ensure_config returns Path to a configuration file in an experiment directory, copying from defaults if this does not exist
def _ensure_config(experiment_dir: Path) -> Path:
    experiment_dir.mkdir(parents=True, exist_ok=True)
    target = experiment_dir / CONFIG_FILENAME
    if not target.exists():
        with resources.as_file(_bundled_default()) as src:
            shutil.copyfile(src, target)
        logMsg.info(f'Wrote default motif config to {target}')
    return target

# -- load_motif_config: returns a MotifConfig containing contents of configuration file in specified experiment directory
def load_motif_config(experiment_dir: Path) -> MotifConfig:
    path = _ensure_config(experiment_dir)
    with path.open('rb') as f:
        table = tomllib.load(f)
    m = table.get('motifs', {})
    return MotifConfig(
        raw=table,
        algorithm=m.get('algorithm'),
        min_width=m.get('min_width'),
        max_width=m.get('max_width'),
        n_motifs=m.get('n_motifs'),
        evalue_threshold=m.get('evalue_threshold'),
        seed=m.get('seed'),
        window=m.get('window'),
        elm_database_version=m.get('elm_database_version', ''),
        motif_library_version=m.get('motif_library_version', ''),
    )