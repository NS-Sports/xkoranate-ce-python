from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QItemDelegate, QLineEdit, QSpinBox

from ...ui.comboindicator import XkorComboIndicatorMixin
from ...variant import toInt, toString


class XkorWC36RPBonusDelegate(XkorComboIndicatorMixin, QItemDelegate):
    def usesComboEditor(self, index):
        return index.column() == 1

    def createEditor(self, parent, option, index):
        if index.column() == 1:
            comboBox = QComboBox(parent)
            comboBox.setFrame(False)
            comboBox.addItem("Slani", 0)
            comboBox.addItem("Poor", 1)
            comboBox.addItem("Good", 2)
            comboBox.addItem("Great", 3)
            comboBox.addItem("Exceptional", 4)
            return self.bindComboEditor(comboBox)
        elif index.column() == 2:
            spinBox = QSpinBox(parent)
            spinBox.setFrame(False)
            return spinBox
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            return lineEdit

    def setEditorData(self, editor, index):
        if index.column() == 1:
            comboBox = editor
            comboBox.setCurrentIndex(comboBox.findText(toString(index.model().data(index, Qt.DisplayRole))))
            # comboBox->setCurrentIndex(comboBox->findData(index.model()->data(index, 1093)));
        elif index.column() == 2:
            spinBox = editor
            spinBox.setValue(toInt(index.model().data(index, Qt.DisplayRole)))
        else:
            lineEdit = editor
            lineEdit.setText(toString(index.model().data(index, Qt.DisplayRole)))

    def setModelData(self, editor, model, index):
        if index.column() == 1:
            comboBox = editor
            model.setData(index, comboBox.currentText())
            model.setData(index, comboBox.itemData(comboBox.currentIndex()), 1093)
        elif index.column() == 2:
            spinBox = editor
            model.setData(index, spinBox.value())
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
