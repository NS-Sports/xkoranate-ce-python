from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

from ..variant import toString


class XkorSortCriteriaDelegate(QStyledItemDelegate):
    def __init__(self, types, names, parent=None):
        super().__init__(parent)
        self.sortTypes = list(types)
        self.sortNames = list(names)

    def createEditor(self, parent, option, index):
        comboBox = QComboBox(parent)
        comboBox.setFrame(False)
        comboBox.insertItems(0, self.sortNames)
        return comboBox

    def setEditorData(self, editor, index):
        comboBox = editor
        comboBox.setCurrentIndex(comboBox.findText(
            toString(index.model().data(index, Qt.DisplayRole))))

    def setModelData(self, editor, model, index):
        comboBox = editor
        name = comboBox.currentText()
        n = self.sortNames.index(name) if name in self.sortNames else -1
        if 0 <= n < len(self.sortTypes):
            model.setData(index, self.sortTypes[n], 1093)
        else:
            model.setData(index, "<unknown sort type %s>" % name, 1093)
        model.setData(index, name)
