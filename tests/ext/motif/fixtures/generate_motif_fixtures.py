'''
comMS motif extension: fixture generation
'''

# -- Import external dependencies
import random
from pathlib import Path

# -- Define variables
AA = 'ACDEFGHIKLMNPQRSTVWY'
PLANTED = 'RFLR'    # example motif (RxLR)

# -- _rand_seq: returns n-long string of random amino acids
def _rand_seq(rng: random.Random, n: int) -> str:
    return ''.join(rng.choice(AA) for _ in range(n))

# -- generate: outputs None but writes a small protein fixture set (foreground/background) with a planted N-terminal motif in foreground
def generate(out_dir: Path, n_fg: int = 24, n_bg: int = 24, seed: int = 0) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    with (out_dir / 'foreground.fa').open('w') as fh:
        for i in range(n_fg):
            seq = _rand_seq(rng, 120)
            seq = seq[:20] + PLANTED + seq[24:]     # plant at a fixed N-terminal site
            fh.write(f'>fg_{i:03d}\n{seq}\n')
    with (out_dir / 'background.fa').open('w') as fh:
        for i in range(n_bg):
            fh.write(f'>bg_{i:03d}\n{_rand_seq(rng, 120)}\n')

# -- Entrypoint
if __name__ == '__main__':
    generate(Path(__file__).resolve().parent / 'data')