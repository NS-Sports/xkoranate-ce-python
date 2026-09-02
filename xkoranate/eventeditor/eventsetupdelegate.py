from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QComboBox, QItemDelegate, QLineEdit

from ..uuids import uuidToString
from ..athlete import BYE_ID, BYE_NAME
from ..variant import toString


BYE_LABEL = "— %s —" % BYE_NAME


class XkorEventSetupDelegate(QItemDelegate):
    def __init__(self, displayNames, IDs, parent=None):
        super().__init__(parent)
        # shared (mutated in place) with XkorEventSetupWidget
        self.availableAthleteNames = displayNames
        self.availableAthletes = IDs
        # a bye is only a valid entry in a knockout bracket, so the widget
        # turns it on and off as the competition type changes
        self.allowBye = False

    def createEditor(self, parent, option, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = QComboBox(parent)
            comboBox.setFrame(False)
            comboBox.insertItems(0, self.choices())
            comboBox.currentIndexChanged.connect(self.prepareToCommit)
            return comboBox
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            lineEdit.textEdited.connect(self.prepareToCommit)
            return lineEdit

    def choices(self):
        """What a slot can be set to: a free participant, or a bye."""
        rval = list(self.availableAthleteNames)
        if self.allowBye:
            rval.insert(0, BYE_LABEL)
        return rval

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
            if self.allowBye and longName == BYE_LABEL:
                id = BYE_ID
            else:
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
            model.setData(index, uuidToString(id), Qt.UserRole)
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
