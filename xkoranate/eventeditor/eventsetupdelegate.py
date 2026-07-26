from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QItemDelegate, QLineEdit

from ..ui.fonts import XkorComboBox

from ..variant import toString


def _uuidToString(u):
    if u is None:  # null QUuid
        return "{00000000-0000-0000-0000-000000000000}"
    return "{%s}" % u


class XkorEventSetupDelegate(QItemDelegate):
    def __init__(self, displayNames, IDs, parent=None):
        super().__init__(parent)
        # shared (mutated in place) with XkorEventSetupWidget
        self.availableAthleteNames = displayNames
        self.availableAthletes = IDs

    def createEditor(self, parent, option, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = XkorComboBox(parent)
            comboBox.setFrame(False)
            comboBox.insertItems(0, self.availableAthleteNames)
            comboBox.currentIndexChanged.connect(self.prepareToCommit)
            return comboBox
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            lineEdit.textEdited.connect(self.prepareToCommit)
            return lineEdit

    def prepareToCommit(self):
        self.commitData.emit(self.sender())

    def setEditorData(self, editor, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = editor
            comboBox.setCurrentIndex(comboBox.findText(toString(index.model().data(index, Qt.DisplayRole))))
        else:
            lineEdit = editor
            lineEdit.setText(toString(index.model().data(index, Qt.DisplayRole)))

    def setModelData(self, editor, model, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = editor
            longName = comboBox.currentText()
            try:
                athleteIndex = self.availableAthleteNames.index(longName)
            except ValueError:
                athleteIndex = -1
            if athleteIndex != -1:
                id = self.availableAthletes[athleteIndex]
            else:
                id = None
                longName = "<unknown participant>"
            model.setData(index, longName)
            model.setData(index, _uuidToString(id), Qt.UserRole)
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
