import sys
from PySide6 import QtWidgets
from Lib.Lib_MainWindow import MainWindow

if __name__ == "__main__":
    application = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())