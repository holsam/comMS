'''
comMS print license to terminal
'''

# -- Import external dependencies
import pydoc
from importlib.resources import files as pkg_files
from rich import print

# -- printLicense: prints the comMS license to terminal and exits
def printLicense():
    with pkg_files('comms').joinpath('../../LICENSE').open('r') as f:
        pydoc.pager(f.read())
        print(f'comMS is distributed under the [bold cyan]GPL-3.0 license[/bold cyan].\n')
    raise SystemExit(0)