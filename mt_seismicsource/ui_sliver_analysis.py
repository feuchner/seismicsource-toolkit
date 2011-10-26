# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_sliver_analysis.ui'
#
# Created: Wed Oct 26 09:37:48 2011
#      by: PyQt4 UI code generator 4.8.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_SliverAnalysis(object):
    def setupUi(self, SliverAnalysis):
        SliverAnalysis.setObjectName(_fromUtf8("SliverAnalysis"))
        SliverAnalysis.resize(819, 594)
        SliverAnalysis.setFocusPolicy(QtCore.Qt.StrongFocus)
        SliverAnalysis.setWindowTitle(QtGui.QApplication.translate("SliverAnalysis", "Sliver Analysis", None, QtGui.QApplication.UnicodeUTF8))
        SliverAnalysis.setSizeGripEnabled(True)
        self.widgetAnalysis = QtGui.QWidget(SliverAnalysis)
        self.widgetAnalysis.setGeometry(QtCore.QRect(0, 10, 321, 111))
        self.widgetAnalysis.setObjectName(_fromUtf8("widgetAnalysis"))
        self.verticalLayoutWidget_3 = QtGui.QWidget(self.widgetAnalysis)
        self.verticalLayoutWidget_3.setGeometry(QtCore.QRect(10, 0, 301, 101))
        self.verticalLayoutWidget_3.setObjectName(_fromUtf8("verticalLayoutWidget_3"))
        self.layoutAnalysis = QtGui.QVBoxLayout(self.verticalLayoutWidget_3)
        self.layoutAnalysis.setMargin(0)
        self.layoutAnalysis.setObjectName(_fromUtf8("layoutAnalysis"))
        self.groupBoxAnalyzeSlivers = QtGui.QGroupBox(self.verticalLayoutWidget_3)
        self.groupBoxAnalyzeSlivers.setTitle(QtGui.QApplication.translate("SliverAnalysis", "Analyze Slivers", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBoxAnalyzeSlivers.setObjectName(_fromUtf8("groupBoxAnalyzeSlivers"))
        self.btnAnalyzeSlivers = QtGui.QPushButton(self.groupBoxAnalyzeSlivers)
        self.btnAnalyzeSlivers.setGeometry(QtCore.QRect(190, 30, 101, 30))
        self.btnAnalyzeSlivers.setText(QtGui.QApplication.translate("SliverAnalysis", "Analyze!", None, QtGui.QApplication.UnicodeUTF8))
        self.btnAnalyzeSlivers.setObjectName(_fromUtf8("btnAnalyzeSlivers"))
        self.labelSliverThreshold = QtGui.QLabel(self.groupBoxAnalyzeSlivers)
        self.labelSliverThreshold.setGeometry(QtCore.QRect(10, 30, 71, 21))
        self.labelSliverThreshold.setText(QtGui.QApplication.translate("SliverAnalysis", "Threshold", None, QtGui.QApplication.UnicodeUTF8))
        self.labelSliverThreshold.setObjectName(_fromUtf8("labelSliverThreshold"))
        self.inputAnalyzeSlivers_2 = QtGui.QLabel(self.groupBoxAnalyzeSlivers)
        self.inputAnalyzeSlivers_2.setGeometry(QtCore.QRect(10, 60, 66, 21))
        self.inputAnalyzeSlivers_2.setText(QtGui.QApplication.translate("SliverAnalysis", "Buffer", None, QtGui.QApplication.UnicodeUTF8))
        self.inputAnalyzeSlivers_2.setObjectName(_fromUtf8("inputAnalyzeSlivers_2"))
        self.progressBarAnalyzeSlivers = QtGui.QProgressBar(self.groupBoxAnalyzeSlivers)
        self.progressBarAnalyzeSlivers.setGeometry(QtCore.QRect(190, 60, 101, 23))
        self.progressBarAnalyzeSlivers.setProperty("value", 24)
        self.progressBarAnalyzeSlivers.setObjectName(_fromUtf8("progressBarAnalyzeSlivers"))
        self.inputAnalyzeSlivers = QtGui.QDoubleSpinBox(self.groupBoxAnalyzeSlivers)
        self.inputAnalyzeSlivers.setGeometry(QtCore.QRect(100, 30, 62, 25))
        self.inputAnalyzeSlivers.setObjectName(_fromUtf8("inputAnalyzeSlivers"))
        self.inputAnalyzeBuffer = QtGui.QDoubleSpinBox(self.groupBoxAnalyzeSlivers)
        self.inputAnalyzeBuffer.setGeometry(QtCore.QRect(100, 60, 62, 25))
        self.inputAnalyzeBuffer.setObjectName(_fromUtf8("inputAnalyzeBuffer"))
        self.layoutAnalysis.addWidget(self.groupBoxAnalyzeSlivers)
        self.table = QtGui.QTableWidget(SliverAnalysis)
        self.table.setGeometry(QtCore.QRect(0, 120, 821, 471))
        self.table.setColumnCount(17)
        self.table.setObjectName(_fromUtf8("table"))
        self.table.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "Dist", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "RefID", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "RefZ", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "RefLon", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(3, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "RefLat", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(4, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "TestID", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(5, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "TestZ", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(6, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "TestLon", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(7, item)
        item = QtGui.QTableWidgetItem()
        item.setText(QtGui.QApplication.translate("SliverAnalysis", "TestLat", None, QtGui.QApplication.UnicodeUTF8))
        self.table.setHorizontalHeaderItem(8, item)

        self.retranslateUi(SliverAnalysis)
        QtCore.QMetaObject.connectSlotsByName(SliverAnalysis)

    def retranslateUi(self, SliverAnalysis):
        item = self.table.horizontalHeaderItem(0)
        item = self.table.horizontalHeaderItem(1)
        item = self.table.horizontalHeaderItem(2)
        item = self.table.horizontalHeaderItem(3)
        item = self.table.horizontalHeaderItem(4)
        item = self.table.horizontalHeaderItem(5)
        item = self.table.horizontalHeaderItem(6)
        item = self.table.horizontalHeaderItem(7)
        item = self.table.horizontalHeaderItem(8)

