import os
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.gui.tools import StringList
from visualizer.visualizer import *

DEBUG = True

class TWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(TWindow, self).__init__()
        self.t = VIANVisualizer2(self)
        # self.addDockWidget(Qt.LeftDockWidgetArea, self.t)

        self.setCentralWidget(self.t)
        self.resize(1200, 800)

        self.show()

def set_style_sheet(app):
    style_sheet = open(os.path.abspath("qt_ui/themes/qt_stylesheet_dark.css"), 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)

def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    if DEBUG:
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)

if __name__ == '__main__':
    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook
    app = QApplication(sys.argv)
    set_style_sheet(app)
    main = VIANVisualizer2()
    sys.exit(app.exec_())

