from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QItemDelegate, QLineEdit

from ...variant import toDouble, toString


class XkorOlympicRPBonusDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 1:
            spinBox = QDoubleSpinBox(parent)
            spinBox.setDecimals(3)
            spinBox.setMinimum(0)
            spinBox.setMaximum(1)
            spinBox.setSingleStep(0.01)
            spinBox.setFrame(False)
            return spinBox
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            return lineEdit

    def setEditorData(self, editor, index):
        if index.column() == 1:
            spinBox = editor
            spinBox.setValue(toDouble(index.model().data(index, Qt.DisplayRole)))
        else:
            lineEdit = editor
            lineEdit.setText(toString(index.model().data(index, Qt.DisplayRole)))

    def setModelData(self, editor, model, index):
        if index.column() == 1:
            spinBox = editor
            model.setData(index, spinBox.value())
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
