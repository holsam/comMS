'''
comMS print version to terminal
'''

# -- Import external dependencies
import tomllib, typer
from importlib.resources import files as pkg_files
from rich import print

# -- printVersion: prints the current comMS version to terminal and exits
def printVersion():
    with pkg_files('comms').joinpath('../../pyproject.toml').open('rb') as f:
        contents = tomllib.load(f)
    print(f"\nRunning comMS version: v{contents['project']['version']}\n")
    raise SystemExit(0)