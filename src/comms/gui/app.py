'''
comMS experiment GUI: app bootstrap
'''

# -- Import external dependencies
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# -- Import internal functions
from comms.gui.main_window import MainWindow

# -- run_app: create the QApplication, show the main window, and run the event loop
def run_app(experiment_dir: Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(experiment_dir=experiment_dir)
    window.show()
    return app.exec()