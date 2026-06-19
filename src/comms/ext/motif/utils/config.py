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

# -- Define dataclass DiscoverConfig to hold configuration for discover command
@dataclass
class DiscoverConfig:
    algorithm: str = 'streme'
    min_width: int = 6
    max_width: int = 15
    n_motifs: int = 5
    evalue_threshold: float = 0.05
    seed: int = 42
    window: str = 'full'

# -- Define dataclass MotifConfig to hold motif configuration
@dataclass
class MotifConfig:
    discover: DiscoverConfig = field(default_factory=DiscoverConfig)
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
    discover = DiscoverConfig(
        algorithm=m.get('discovery_algorithm', 'streme'),
        min_width=int(m.get('discovery_min_width', 6)),
        max_width=int(m.get('discovery_max_width', 15)),
        n_motifs=int(m.get('discovery_n_motifs', 5)),
        evalue_threshold=float(m.get('discovery_evalue_threshold', 0.05)),
        seed=int(m.get('discovery_seed', 42)),
        window=m.get('sequence_window_default', 'full'),
    )
    return MotifConfig(
        discover=discover,
        raw=table,
        elm_database_version=m.get('elm_database_version', ''),
        motif_library_version=m.get('motif_library_version', ''),
    )