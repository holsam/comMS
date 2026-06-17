'''
comMS CLI subcommand for uninstalling comMS
'''

# -- Import external dependencies
import typer
from typing import Annotated

# -- Import internal functions
from comms.commands import uninstall as uninstallFuncs

# -- Initialise uninstall Typer class
commsUninstall = typer.Typer(add_completion=False)

# -- uninstall: removes comMS-generated files and prints the package-removal command
@commsUninstall.command(help='Remove comMS-generated files and display command to uninstall comMS', rich_help_panel='Utilities')
def uninstall(
    force: Annotated[
        bool,
        typer.Option('--force', help='Skip confirmation before deleting generated files')
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option('--dry-run', help='List what would be removed without deleting anything')
    ] = False,
):
    uninstallFuncs.run_uninstall(force=force, dry_run=dry_run)