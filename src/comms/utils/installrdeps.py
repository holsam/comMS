'''
comMS R dependency wrapper utilities
'''

# -- Import external dependencies
import json, shutil, subprocess
from importlib.resources import files as pkg_files
from pathlib import Path

# -- Import internal functions
from comms.utils.log import logMsg

# -- _r_script: returns Path to a script under comms/r/
def _r_script(name: str) -> Path:
    return pkg_files('comms').joinpath(f'r/{name}')

# -- check_r_dependencies: returns {'installed': [...], 'missing': [...]}, or None if Rscript itself isn't callable / the check failed
def check_r_dependencies(rscript: str = 'Rscript') -> dict[str, list[str]] | None:
    if shutil.which(rscript) is None:
        logMsg.debug(f'Rscript not callable: {rscript}')
        return None
    script_path = _r_script('/deps/check_deps.R')
    result = subprocess.run([rscript, '--vanilla', str(script_path)], capture_output=True, text=True)
    if result.returncode != 0:
        logMsg.debug(f'Dependency check failed: {result.stderr}')
        return None
    try:
        return json.loads(result.stdout.strip())
    except Exception as e:
        logMsg.debug(f'Could not parse depencency check output: {e}')
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