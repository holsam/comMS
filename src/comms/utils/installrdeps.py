'''
comMS R dependency wrapper utilities
'''

# -- Import external dependencies
import json, shutil, subprocess
from importlib.resources import files as pkg_files
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg

# -- _r_script: returns Path to a script under comms/r/
def _r_script(name: str) -> Path:
    return pkg_files('comms').joinpath(f'r/{name}')

# -- _print_dependency_table: returns None but prints a table to output which lists installed/unavailable dependencies
def _print_dependency_table(deps_dict: dict[str, list[str]]) -> None:
    installed_deps = deps_dict['installed']
    missing_deps = deps_dict['missing']
    if len(installed_deps) > 0:
        print(f'[bold]Installed packages ({len(installed_deps)})[/bold]')
        for d in installed_deps:
            print(f'\t[bold green]✓[/bold green] {d}')
    if len(missing_deps) > 0:
        print(f'[bold]Missing packages ({len(missing_deps)})[/bold]')
        for d in missing_deps:
            print(f'\t[bold red]✗[/bold red] {d}')
        print('\nTo install missing packages, run [bold]comms r-utils install[/bold]')

# -- check_r_dependencies: returns {'installed': [...], 'missing': [...]}, or None if Rscript itself isn't callable / the check failed
def check_r_dependencies(rscript: str = 'Rscript') -> dict[str, list[str]] | None:
    if shutil.which(rscript) is None:
        logMsg.error(f'Rscript not callable: {rscript}')
        return None
    logMsg.debug(f'R available at {rscript}')
    script_path = _r_script('/deps/check_deps.R')
    result = subprocess.run([rscript, '--vanilla', str(script_path)], capture_output=True, text=True)
    logMsg.debug(f'R dependency check ran successfully')
    if result.returncode != 0:
        logMsg.warn(f'Dependency check failed: {result.stderr}')
        return None
    # Parse returned result as JSON
    try:
        parsed = json.loads(result.stdout.strip())
        _print_dependency_table(parsed)
        return parsed
    except Exception as e:
        logMsg.error(f'Could not parse depencency check output: {e}')
        return None

# -- install_r_dependencies: runs install_deps.R, streaming its messages through logMsg.info; returns True on success (including "nothing to do")
def install_r_dependencies(rscript: str = 'Rscript') -> bool:
    if shutil.which(rscript) is None:
        logMsg.error(f'Rscript not callable: {rscript}')
        return False
    script_path = _r_script('deps/install_deps.R')
    logMsg.info('Installing R report dependencies (this can take a few minutes)...')
    process = subprocess.Popen(
        [rscript, '--vanilla', str(script_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for line in process.stdout:
        line = line.rstrip()
        if line:
            logMsg.info(line)
    process.wait()
    if process.returncode != 0:
        logMsg.error('R dependency installation failed; see above output')
        return False
    logMsg.info('All R report dependencies installed')
    return True

# -- install_r_dependencies_terminal: wrapper for install_r_dependencies to print confirm installation
def install_r_dependencies_terminal(rscript: str = 'Rscript') -> None:
    # Check that Rscript is available
    if shutil.which(rscript) is None:
        logMsg.error(f'Rscript not callable: {rscript}')
        raise SystemExit(1)
    # Check if anything needs installing
    try:
        script_path = _r_script('/deps/check_deps.R')
        result = subprocess.run([rscript, '--vanilla', str(script_path)], capture_output=True, text=True)
        parsed = json.loads(result.stdout.strip())
        missing = parsed['missing']
        if len(missing) > 0:
            logMsg.info(f'{len(missing)} {'dependencies need' if len(missing) > 1 else 'dependency needs'} to be installed: {', '.join(d for d in missing)}')
            while True:
                user_confirmation = input('Install these packages? (y/N)').lower()
                if user_confirmation in ['', 'n']:
                    logMsg.info(f'Cancelled dependency installation.')
                    break
                if user_confirmation == 'y':
                    install_r_dependencies()
                    break
        else:
            logMsg.info(f'No dependencies missing')
    except Exception as e:
        logMsg.error(f'Error while checking for missing dependencies: {e}')