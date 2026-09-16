from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QComboBox, QItemDelegate, QLineEdit

from ..athlete import BYE_ID, BYE_NAME
from ..ui.comboindicator import XkorComboIndicatorMixin
from ..variant import toString


BYE_LABEL = "— %s —" % BYE_NAME


def _uuidToString(u):
    if u is None:  # null QUuid
        return "{00000000-0000-0000-0000-000000000000}"
    return "{%s}" % u


class XkorEventSetupDelegate(XkorComboIndicatorMixin, QItemDelegate):
    def __init__(self, displayNames, IDs, parent=None):
        super().__init__(parent)
        # shared (mutated in place) with XkorEventSetupWidget
        self.availableAthleteNames = displayNames
        self.availableAthletes = IDs
        # a bye is only a valid entry in a knockout bracket, so the widget
        # turns it on and off as the competition type changes
        self.allowBye = False

    def usesComboEditor(self, index):
        return index.parent() != QModelIndex()  # a participant, not a group name

    def createEditor(self, parent, option, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = QComboBox(parent)
            comboBox.setFrame(False)
            for label, id in self.choices(self.currentName(index), self.currentId(index)):
                comboBox.addItem(label, id)
            comboBox.currentIndexChanged.connect(self.prepareToCommit)
            return self.bindComboEditor(comboBox)
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            lineEdit.textEdited.connect(self.prepareToCommit)
            return lineEdit

    def currentName(self, index):
        return toString(index.model().data(index, Qt.DisplayRole))

    def currentId(self, index):
        return toString(index.model().data(index, Qt.UserRole))

    def choices(self, current=None, currentId=None):
        """What a slot can be set to, as (label, id) pairs: whoever is in it,
        a free participant, or a bye.

        The id travels with the entry rather than being looked back up from
        the label, because two participants can share a name and nation —
        resolving by name took whichever came first, so picking the second
        placed the first.

        Only unplaced participants are on offer — putting someone in two
        slots at once isn't a thing — but the one already here has to be
        listed as well, or opening the editor on an occupied slot would find
        nothing selected and blank it on the way out.
        """
        rval = [(name, _uuidToString(id)) for name, id
                in zip(self.availableAthleteNames, self.availableAthletes)]
        if current and current != BYE_LABEL \
                and currentId not in [id for _, id in rval]:
            rval.insert(0, (current, currentId))
        if self.allowBye:
            rval.insert(0, (BYE_LABEL, _uuidToString(BYE_ID)))
        return rval

    def prepareToCommit(self):
        self.commitData.emit(self.sender())

    def setEditorData(self, editor, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = editor
            # by id, not by label: two entries can carry the same text
            comboBox.setCurrentIndex(comboBox.findData(self.currentId(index)))
        else:
            lineEdit = editor
            lineEdit.setText(toString(index.model().data(index, Qt.DisplayRole)))

    def setModelData(self, editor, model, index):
        if index.parent() != QModelIndex():  # if this is an athlete, not a group name
            comboBox = editor
            longName = comboBox.currentText()
            id = comboBox.currentData()
            if longName == "" or id is None or id == self.currentId(index):
                return  # nothing was chosen; leave the slot as it was

            model.setData(index, longName)
            model.setData(index, id, Qt.UserRole)
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
