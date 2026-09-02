from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QComboBox, QItemDelegate, QLineEdit

from ..athlete import BYE_ID, BYE_NAME
from ..variant import toString


BYE_LABEL = "— %s —" % BYE_NAME


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
        # a bye is only a valid entry in a knockout bracket, so the widget
        # turns it on and off as the competition type changes
        self.allowBye = False

    def createEditor(self, parent, option, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = QComboBox(parent)
            comboBox.setFrame(False)
            comboBox.insertItems(0, self.choices(self.currentName(index)))
            comboBox.currentIndexChanged.connect(self.prepareToCommit)
            return comboBox
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            lineEdit.textEdited.connect(self.prepareToCommit)
            return lineEdit

    def currentName(self, index):
        return toString(index.model().data(index, Qt.DisplayRole))

    def choices(self, current=None):
        """What a slot can be set to: whoever is in it, a free participant,
        or a bye.

        Only unplaced participants are on offer — putting someone in two
        slots at once isn't a thing — but the one already here has to be
        listed as well, or opening the editor on an occupied slot would find
        nothing selected and blank it on the way out.
        """
        rval = list(self.availableAthleteNames)
        if current and current != BYE_LABEL and current not in rval:
            rval.insert(0, current)
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
            if longName == "" or longName == self.currentName(index):
                return  # nothing was chosen; leave the slot as it was

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
            model.setData(index, _uuidToString(id), Qt.UserRole)
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
