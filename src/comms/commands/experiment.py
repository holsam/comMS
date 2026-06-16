'''
comMS experiment functions
'''

# -- Import internal functions
from comms.utils.log import logMsg

# -- launch_experiment_gui: opens the PySide6 experiment setup window
def launch_experiment_gui() -> None:
    logMsg('experiment')
    try:
        from comms.gui.app import run_app
    except ImportError as e:
        logMsg.error(f'Could not import GUI components: {e}')
        raise SystemExit(1)
    logMsg.info(f'Launching experiment setup GUI')
    raise SystemExit(run_app())