# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_ImageAlignmentTJbVQF.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QGroupBox,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QTextBrowser,
    QToolButton, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(1658, 1072)
        self.groupBox = QGroupBox(Dialog)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(760, 10, 891, 71))
        font = QFont()
        font.setPointSize(12)
        self.groupBox.setFont(font)
        self.bg_img_dir_path = QLineEdit(self.groupBox)
        self.bg_img_dir_path.setObjectName(u"bg_img_dir_path")
        self.bg_img_dir_path.setGeometry(QRect(230, 30, 501, 31))
        self.bg_img_load = QPushButton(self.groupBox)
        self.bg_img_load.setObjectName(u"bg_img_load")
        self.bg_img_load.setGeometry(QRect(780, 30, 101, 31))
        self.bg_img_dir = QLabel(self.groupBox)
        self.bg_img_dir.setObjectName(u"bg_img_dir")
        self.bg_img_dir.setGeometry(QRect(10, 30, 280, 31))
        self.bg_img_open_dir = QToolButton(self.groupBox)
        self.bg_img_open_dir.setObjectName(u"bg_img_open_dir")
        self.bg_img_open_dir.setGeometry(QRect(740, 30, 31, 31))
        self.groupBox_2 = QGroupBox(Dialog)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setGeometry(QRect(10, 90, 1641, 581))
        self.groupBox_2.setFont(font)
        self.gridLayout = QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_4 = QGroupBox(self.groupBox_2)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_4 = QGridLayout(self.groupBox_4)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.label_6 = QLabel(self.groupBox_4)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_4.addWidget(self.label_6, 0, 0, 1, 1)

        self.label_5 = QLabel(self.groupBox_4)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_4.addWidget(self.label_5, 0, 1, 1, 1)

        self.label_7 = QLabel(self.groupBox_4)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_4.addWidget(self.label_7, 0, 2, 1, 1)

        self.label_8 = QLabel(self.groupBox_4)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_4.addWidget(self.label_8, 0, 3, 1, 1)


        self.gridLayout.addWidget(self.groupBox_4, 2, 0, 1, 3)

        self.groupBox_3 = QGroupBox(self.groupBox_2)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_3 = QGridLayout(self.groupBox_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label = QLabel(self.groupBox_3)
        self.label.setObjectName(u"label")

        self.gridLayout_3.addWidget(self.label, 0, 2, 3, 1)

        self.label_2 = QLabel(self.groupBox_3)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_3.addWidget(self.label_2, 0, 0, 3, 1)

        self.label_3 = QLabel(self.groupBox_3)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_3.addWidget(self.label_3, 0, 4, 3, 1)

        self.label_4 = QLabel(self.groupBox_3)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_3.addWidget(self.label_4, 0, 5, 3, 1)


        self.gridLayout.addWidget(self.groupBox_3, 0, 0, 1, 3)

        self.pushButton_2 = QPushButton(Dialog)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setGeometry(QRect(10, 680, 450, 40))
        self.pushButton_2.setFont(font)
        self.tableWidget = QTableWidget(Dialog)
        if (self.tableWidget.columnCount() < 4):
            self.tableWidget.setColumnCount(4)
        font1 = QFont()
        font1.setFamilies([u"MS Shell Dlg 2"])
        font1.setPointSize(12)
        font1.setBold(True)
        __qtablewidgetitem = QTableWidgetItem()
        __qtablewidgetitem.setFont(font1);
        self.tableWidget.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        __qtablewidgetitem1.setFont(font1);
        self.tableWidget.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        __qtablewidgetitem2.setFont(font1);
        self.tableWidget.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        __qtablewidgetitem3.setFont(font1);
        self.tableWidget.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        if (self.tableWidget.rowCount() < 50):
            self.tableWidget.setRowCount(50)
        self.tableWidget.setObjectName(u"tableWidget")
        self.tableWidget.setGeometry(QRect(10, 730, 450, 281))
        font2 = QFont()
        font2.setFamilies([u"MS Shell Dlg 2"])
        font2.setPointSize(12)
        self.tableWidget.setFont(font2)
        self.tableWidget.setRowCount(50)
        self.tableWidget.setColumnCount(4)
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(False)
        self.pushButton_3 = QPushButton(Dialog)
        self.pushButton_3.setObjectName(u"pushButton_3")
        self.pushButton_3.setGeometry(QRect(490, 680, 321, 40))
        self.pushButton_3.setFont(font)
        self.textBrowser = QTextBrowser(Dialog)
        self.textBrowser.setObjectName(u"textBrowser")
        self.textBrowser.setGeometry(QRect(490, 730, 651, 331))
        self.textBrowser.setFont(font)
        self.image_save_3 = QGroupBox(Dialog)
        self.image_save_3.setObjectName(u"image_save_3")
        self.image_save_3.setGeometry(QRect(1160, 680, 491, 111))
        font3 = QFont()
        font3.setPointSize(12)
        font3.setBold(False)
        font3.setUnderline(False)
        self.image_save_3.setFont(font3)
        self.folder_save_open_dir_3 = QToolButton(self.image_save_3)
        self.folder_save_open_dir_3.setObjectName(u"folder_save_open_dir_3")
        self.folder_save_open_dir_3.setGeometry(QRect(330, 70, 31, 31))
        self.folder_save_path_3 = QLineEdit(self.image_save_3)
        self.folder_save_path_3.setObjectName(u"folder_save_path_3")
        self.folder_save_path_3.setGeometry(QRect(10, 70, 311, 31))
        self.img_dir_3 = QLabel(self.image_save_3)
        self.img_dir_3.setObjectName(u"img_dir_3")
        self.img_dir_3.setGeometry(QRect(10, 30, 110, 31))
        self.bg_img_load_2 = QPushButton(self.image_save_3)
        self.bg_img_load_2.setObjectName(u"bg_img_load_2")
        self.bg_img_load_2.setGeometry(QRect(380, 70, 101, 31))
        self.pushButton_4 = QPushButton(Dialog)
        self.pushButton_4.setObjectName(u"pushButton_4")
        self.pushButton_4.setGeometry(QRect(10, 1020, 221, 40))
        self.pushButton_4.setFont(font)
        self.pushButton_5 = QPushButton(Dialog)
        self.pushButton_5.setObjectName(u"pushButton_5")
        self.pushButton_5.setGeometry(QRect(250, 1020, 211, 40))
        self.pushButton_5.setFont(font)
        self.groupBox_5 = QGroupBox(Dialog)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.groupBox_5.setGeometry(QRect(10, 10, 741, 71))
        self.groupBox_5.setFont(font)
        self.bg_img_dir_path_2 = QLineEdit(self.groupBox_5)
        self.bg_img_dir_path_2.setObjectName(u"bg_img_dir_path_2")
        self.bg_img_dir_path_2.setGeometry(QRect(150, 30, 411, 31))
        self.bg_img_load_3 = QPushButton(self.groupBox_5)
        self.bg_img_load_3.setObjectName(u"bg_img_load_3")
        self.bg_img_load_3.setGeometry(QRect(610, 30, 120, 31))
        self.bg_img_dir_3 = QLabel(self.groupBox_5)
        self.bg_img_dir_3.setObjectName(u"bg_img_dir_3")
        self.bg_img_dir_3.setGeometry(QRect(10, 30, 141, 31))
        self.bg_img_open_dir_2 = QToolButton(self.groupBox_5)
        self.bg_img_open_dir_2.setObjectName(u"bg_img_open_dir_2")
        self.bg_img_open_dir_2.setGeometry(QRect(570, 30, 31, 31))
        self.pushButton_6 = QPushButton(Dialog)
        self.pushButton_6.setObjectName(u"pushButton_6")
        self.pushButton_6.setGeometry(QRect(1500, 990, 151, 61))
        self.pushButton_6.setFont(font)
        self.pushButton = QPushButton(Dialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(820, 680, 311, 41))
        self.pushButton.setFont(font)
        self.groupBox_2.raise_()
        self.groupBox.raise_()
        self.pushButton_2.raise_()
        self.tableWidget.raise_()
        self.pushButton_3.raise_()
        self.textBrowser.raise_()
        self.image_save_3.raise_()
        self.pushButton_4.raise_()
        self.pushButton_5.raise_()
        self.groupBox_5.raise_()
        self.pushButton_6.raise_()
        self.pushButton.raise_()

        self.retranslateUi(Dialog)

        #QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", u"Load Existing Configuration File", None))
        self.bg_img_load.setText(QCoreApplication.translate("Dialog", u"Load File", None))
        self.bg_img_dir.setText(QCoreApplication.translate("Dialog", u"Configuration File Source (.ini):", None))
        self.bg_img_open_dir.setText(QCoreApplication.translate("Dialog", u"...", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Dialog", u"Manual Feature Detection and Description", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("Dialog", u"Zoom Frame", None))
        self.label_6.setText("")
        self.label_5.setText("")
        self.label_7.setText("")
        self.label_8.setText("")
        self.groupBox_3.setTitle(QCoreApplication.translate("Dialog", u"Full Frame", None))
        self.label.setText("")
        self.label_2.setText("")
        self.label_3.setText("")
        self.label_4.setText("")
        self.pushButton_2.setText(QCoreApplication.translate("Dialog", u"Add Point", None))
        ___qtablewidgetitem = self.tableWidget.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("Dialog", u"(y0,x0)", None));
        ___qtablewidgetitem1 = self.tableWidget.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("Dialog", u"(y1,x1)", None));
        ___qtablewidgetitem2 = self.tableWidget.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("Dialog", u"(y2,x2)", None));
        ___qtablewidgetitem3 = self.tableWidget.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("Dialog", u"(y3,x3)", None));
        self.pushButton_3.setText(QCoreApplication.translate("Dialog", u"Estimate Transformation", None))
        self.image_save_3.setTitle(QCoreApplication.translate("Dialog", u"Transformation Configuration Save", None))
        self.folder_save_open_dir_3.setText(QCoreApplication.translate("Dialog", u"...", None))
        self.img_dir_3.setText(QCoreApplication.translate("Dialog", u"Output Folder:", None))
        self.bg_img_load_2.setText(QCoreApplication.translate("Dialog", u"Save", None))
        self.pushButton_4.setText(QCoreApplication.translate("Dialog", u"Reset", None))
        self.pushButton_5.setText(QCoreApplication.translate("Dialog", u"Delete", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("Dialog", u"Load Calibration Image", None))
        self.bg_img_load_3.setText(QCoreApplication.translate("Dialog", u"Load Images", None))
        self.bg_img_dir_3.setText(QCoreApplication.translate("Dialog", u"Calibration Images:", None))
        self.bg_img_open_dir_2.setText(QCoreApplication.translate("Dialog", u"...", None))
        self.pushButton_6.setText(QCoreApplication.translate("Dialog", u"Apply", None))
        self.pushButton.setText(QCoreApplication.translate("Dialog", u"Automatic Transformation Estimation", None))
    # retranslateUi

