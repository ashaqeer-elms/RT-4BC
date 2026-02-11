# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_MainWindowtsvxiC.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QMainWindow, QSizePolicy,
    QStatusBar, QTabWidget, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setWindowModality(Qt.WindowModality.WindowModal)
        MainWindow.resize(1917, 1161)
        font = QFont()
        font.setPointSize(12)
        MainWindow.setFont(font)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.main_tab = QTabWidget(self.centralwidget)
        self.main_tab.setObjectName(u"main_tab")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.main_tab.sizePolicy().hasHeightForWidth())
        self.main_tab.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setPointSize(12)
        font1.setUnderline(False)
        self.main_tab.setFont(font1)
        self.main_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.camera_viewer = QWidget()
        self.camera_viewer.setObjectName(u"camera_viewer")
        self.main_tab.addTab(self.camera_viewer, "")
        self.calibration = QWidget()
        self.calibration.setObjectName(u"calibration")
        self.main_tab.addTab(self.calibration, "")
        self.raster_calculation = QWidget()
        self.raster_calculation.setObjectName(u"raster_calculation")
        self.main_tab.addTab(self.raster_calculation, "")
        self.classification = QWidget()
        self.classification.setObjectName(u"classification")
        self.main_tab.addTab(self.classification, "")

        self.gridLayout.addWidget(self.main_tab, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusBar = QStatusBar(MainWindow)
        self.statusBar.setObjectName(u"statusBar")
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)

        self.main_tab.setCurrentIndex(0)


        #QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.main_tab.setTabText(self.main_tab.indexOf(self.camera_viewer), QCoreApplication.translate("MainWindow", u"Camera Viewer", None))
        self.main_tab.setTabText(self.main_tab.indexOf(self.calibration), QCoreApplication.translate("MainWindow", u"Calibration", None))
        self.main_tab.setTabText(self.main_tab.indexOf(self.raster_calculation), QCoreApplication.translate("MainWindow", u"Raster Calculation", None))
        self.main_tab.setTabText(self.main_tab.indexOf(self.classification), QCoreApplication.translate("MainWindow", u"Classification", None))
    # retranslateUi

