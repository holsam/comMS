'''
comMS experiment GUI: main window
'''

# -- Import external dependencies
from PySide6.QtWidgets import QMainWindow, QLabel

# -- Define class MainWindow
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('comMS')
        self.resize(1100, 720)
        self.setCentralWidget(QLabel('Experiment Setup'))