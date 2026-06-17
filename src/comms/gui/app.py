'''
comMS experiment GUI: app bootstrap
'''

# -- Import external dependencies
import sys
from PySide6.QtWidgets import QApplication

# -- Import internal functions
from comms.gui.main_window import MainWindow

# -- run_app: create the QApplication, show the main window, and run the event loop
def run_app() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()