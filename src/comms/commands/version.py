'''
comMS print version to terminal
'''

# -- Import external dependencies
from importlib.metadata import version, PackageNotFoundError
from rich import print

# -- printVersion: prints the current comMS version to terminal and exits
def printVersion():
    try:
        ver = version('comms')
    except PackageNotFoundError:
        ver = 'unknown (package not installed)'
    print(f'Running comMS version: v{ver}\n')
    raise SystemExit(0)