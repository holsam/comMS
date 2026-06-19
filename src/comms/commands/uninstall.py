'''
comMS uninstall command functions
'''

# -- Import external dependencies
import sys, typer
from pathlib import Path
from rich import print

# -- Import internal classes/functionsc
from comms.utils.log import logMsg
from comms.utils.settings import globalConfigPath

# -- _generated_targets: returns a list of Paths to files/directories created by comMS
def _generated_targets() -> list[Path]:
    '''
    Collect files and directories comMS has created outside of analysis outputs
    '''
    targets: list[Path] = []
    config_path = globalConfigPath()
    if config_path.exists():
        targets.append(config_path)
    # Only include config directory if it only holds comMS-created files
    config_dir = config_path.parent
    if config_dir.exists() and config_dir.name == 'comms':
        remaining = [p for p in config_dir.iterdir() if p != config_path]
        if not remaining:
            targets.append(config_dir)
    return targets


# -- _detect_uninstall_command: returns a string for uninstalling comms (best-effort approach)
def _detect_uninstall_command() -> str:
    '''
    Infer how comMS was installed from the launching executable path
    '''
    # Check if installed using uv tool install
    try:
        exe = Path(sys.argv[0]).resolve()
        parts = {p.lower() for p in exe.parts}
        if 'uv' in parts and 'tools' in parts:
            return 'uv tool uninstall comms'
    except Exception:
        pass
    # Check if installed with pip
    try:
        import subprocess
        pip_pkgs = subprocess.run(['python', '-m', 'pip', 'list'], capture_output=True, check=True).stdout.decode(sys.stdout.encoding)
        # Split output into list of packages (represented as lists with name and version)
        pip_pkgs = [p.split() for p in pip_pkgs.split('\n')]
        # Flatten list
        pip_pkgs = [p for pkg in pip_pkgs for p in pkg]
        if 'comms' in pip_pkgs:
            return 'pip uninstall comms'
        else:
            pass
    except Exception:
        pass
    # Return unknown
    return '(unknown installation method used, uninstall using package manager)'

# -- run_uninstall: remove generated files and print the package-removal command
def run_uninstall(force: bool = False, dry_run: bool = False) -> None:
    logMsg('uninstall')
    logMsg.debug('Started command: uninstall')
    targets = _generated_targets()
    if not targets:
        logMsg.info('No comMS-generated files found to remove')
    else:
        print('[bold]The following comMS-generated paths will be removed:[/bold]')
        for t in targets:
            print(f'  [cyan]{t}[/cyan]')
        if dry_run:
            logMsg.info('Dry run: nothing was deleted')
            return
        if not force and not typer.confirm('Delete these paths?'):
            logMsg.info('Cancelled comMS uninstall')
            raise SystemExit(0)
        for t in targets:
            try:
                if t.is_dir():
                    t.rmdir()
                else:
                    t.unlink()
                logMsg.progress(f'Removed {t}')
            except OSError as e:
                logMsg.warn(f'Could not remove {t}: {e}')
        logMsg.info('Generated files removed')
    cmd = _detect_uninstall_command()
    print(
        f'\nTo finish removing comMS, run:\n'
        f'[bold]{cmd}[/bold]\n'
        f'(If that command does not match how you installed comMS, use your package manager\'s uninstall command instead).\n'
    )
    logMsg.debug('Finished command: uninstall')