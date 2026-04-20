'''
comMS entry point shim: re-exports the root typer app from cli.main so that the pyproject.toml script target (comms.main:comms) works.
'''
from comms.cli.cli import comms

__all__ = ["comms"]