'''
comMS print license to terminal
'''

# -- Import external dependencies
import typer
from importlib.resources import files as pkg_files
from rich import print

# -- printLicense: prints the comMS license to terminal and exits
def printLicense():
    with pkg_files('comms').joinpath('../../LICENSE').open('r') as f:
        print(f'\n{f.read()}')
    raise SystemExit(0)