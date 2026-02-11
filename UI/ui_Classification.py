# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_ClassificationOAkXqJ.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QToolButton, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1907, 1100)
        self.class_view = QGroupBox(Form)
        self.class_view.setObjectName(u"class_view")
        self.class_view.setGeometry(QRect(420, 130, 1471, 851))
        font = QFont()
        font.setPointSize(12)
        self.class_view.setFont(font)
        self.class_img = QLabel(self.class_view)
        self.class_img.setObjectName(u"class_img")
        self.class_img.setGeometry(QRect(10, 20, 1451, 821))
        self.img_legend = QLabel(Form)
        self.img_legend.setObjectName(u"img_legend")
        self.img_legend.setGeometry(QRect(430, 19, 1461, 101))
        self.img_legend.setFont(font)
        self.image_save_4 = QGroupBox(Form)
        self.image_save_4.setObjectName(u"image_save_4")
        self.image_save_4.setGeometry(QRect(10, 940, 381, 141))
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(False)
        font1.setUnderline(False)
        self.image_save_4.setFont(font1)
        self.img_save_act_4 = QCheckBox(self.image_save_4)
        self.img_save_act_4.setObjectName(u"img_save_act_4")
        self.img_save_act_4.setGeometry(QRect(240, 110, 140, 31))
        self.folder_save_open_dir_4 = QToolButton(self.image_save_4)
        self.folder_save_open_dir_4.setObjectName(u"folder_save_open_dir_4")
        self.folder_save_open_dir_4.setGeometry(QRect(340, 70, 31, 31))
        self.folder_save_path_4 = QLineEdit(self.image_save_4)
        self.folder_save_path_4.setObjectName(u"folder_save_path_4")
        self.folder_save_path_4.setGeometry(QRect(10, 70, 321, 31))
        self.img_dir_4 = QLabel(self.image_save_4)
        self.img_dir_4.setObjectName(u"img_dir_4")
        self.img_dir_4.setGeometry(QRect(10, 30, 110, 31))
        self.class_input = QGroupBox(Form)
        self.class_input.setObjectName(u"class_input")
        self.class_input.setGeometry(QRect(10, 10, 381, 491))
        self.class_input.setFont(font)
        self.model_file_dir = QLabel(self.class_input)
        self.model_file_dir.setObjectName(u"model_file_dir")
        self.model_file_dir.setGeometry(QRect(10, 30, 290, 31))
        self.model_path_dir = QLineEdit(self.class_input)
        self.model_path_dir.setObjectName(u"model_path_dir")
        self.model_path_dir.setGeometry(QRect(10, 70, 321, 31))
        self.model_load = QPushButton(self.class_input)
        self.model_load.setObjectName(u"model_load")
        self.model_load.setGeometry(QRect(270, 110, 101, 31))
        self.model_open_dir = QToolButton(self.class_input)
        self.model_open_dir.setObjectName(u"model_open_dir")
        self.model_open_dir.setGeometry(QRect(340, 70, 31, 31))
        self.model_input_sel = QLabel(self.class_input)
        self.model_input_sel.setObjectName(u"model_input_sel")
        self.model_input_sel.setGeometry(QRect(10, 150, 140, 31))
        self.model_input = QListWidget(self.class_input)
        self.model_input.setObjectName(u"model_input")
        self.model_input.setGeometry(QRect(10, 190, 361, 251))
        self.model_apply = QPushButton(self.class_input)
        self.model_apply.setObjectName(u"model_apply")
        self.model_apply.setGeometry(QRect(280, 450, 80, 30))
        self.class_en_segment = QCheckBox(Form)
        self.class_en_segment.setObjectName(u"class_en_segment")
        self.class_en_segment.setEnabled(False)
        self.class_en_segment.setGeometry(QRect(1710, 990, 180, 31))
        self.class_en_segment.setFont(font)
        self.model_code_up = QPushButton(Form)
        self.model_code_up.setObjectName(u"model_code_up")
        self.model_code_up.setEnabled(False)
        self.model_code_up.setGeometry(QRect(1780, 1030, 111, 51))
        self.model_code_up.setFont(font)
        self.class_en_segment_2 = QCheckBox(Form)
        self.class_en_segment_2.setObjectName(u"class_en_segment_2")
        self.class_en_segment_2.setGeometry(QRect(420, 990, 180, 31))
        self.class_en_segment_2.setFont(font)
        self.class_en_segment_2.setChecked(True)

        self.retranslateUi(Form)

        #QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.class_view.setTitle(QCoreApplication.translate("Form", u"Classification Viewer", None))
        self.class_img.setText("")
        self.img_legend.setText(QCoreApplication.translate("Form", u"CLASS_LEGEND", None))
        self.image_save_4.setTitle(QCoreApplication.translate("Form", u"Classification Image Save", None))
        self.img_save_act_4.setText(QCoreApplication.translate("Form", u"  Save Image(s)", None))
        self.folder_save_open_dir_4.setText(QCoreApplication.translate("Form", u"...", None))
        self.img_dir_4.setText(QCoreApplication.translate("Form", u"Output Folder:", None))
        self.class_input.setTitle(QCoreApplication.translate("Form", u"Input Classification Model", None))
        self.model_file_dir.setText(QCoreApplication.translate("Form", u"Classification Model File Source (.joblib):", None))
        self.model_load.setText(QCoreApplication.translate("Form", u"Load File", None))
        self.model_open_dir.setText(QCoreApplication.translate("Form", u"...", None))
        self.model_input_sel.setText(QCoreApplication.translate("Form", u"Select Model Input:", None))
        self.model_apply.setText(QCoreApplication.translate("Form", u"Apply", None))
        self.class_en_segment.setText(QCoreApplication.translate("Form", u" Enable Segmentation", None))
        self.model_code_up.setText(QCoreApplication.translate("Form", u"Upload", None))
        self.class_en_segment_2.setText(QCoreApplication.translate("Form", u"Auto Classify", None))
    # retranslateUi

