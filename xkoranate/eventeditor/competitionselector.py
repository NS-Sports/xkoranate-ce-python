from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QWidget

from ..ui.fonts import XkorComboBox
from ..ui.typography import heading_label
from ..variant import toString


class XkorCompetitionSelector(QWidget):
    competitionChanged = Signal(str)
    competitionOptionsChanged = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.optionsWidget = None
        self.currentOptions = {}

        self.comboBox = XkorComboBox()
        self.comboBox.setInsertPolicy(QComboBox.InsertAlphabetically)
        # its items are replaced whenever the sport changes (setSport()), and
        # XkorComboBox keeps it sized to the current items rather than to
        # whatever was longest the first time it was shown
        self.comboBox.currentIndexChanged.connect(self.updateCompetition)

        self.layout = QGridLayout(self)
        label = heading_label("Choose competition type", level=1, center=True)
        self.layout.addWidget(label, 0, 0, Qt.AlignCenter)
        self.layout.addWidget(self.comboBox, 1, 0, Qt.AlignTop | Qt.AlignHCenter)
        self.layout.setRowStretch(0, 0)
        self.layout.setRowStretch(1, 0)
        self.layout.setRowStretch(2, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.updateCompetition(-1)  # show a big competition options widget so that the layout has room for it

    def setCompetition(self, competition):
        index = self.comboBox.findData(competition, Qt.UserRole)
        self.comboBox.setCurrentIndex(index)
        self.updateCompetition(index)

    def setSport(self, sport, paradigmOptions):
        self.currentOptions = paradigmOptions

        from ..paradigms.paradigmfactory import XkorParadigmFactory

        p = XkorParadigmFactory.newParadigmForSport(sport, paradigmOptions)

        # update the competition types list
        currentCompetitionType = toString(self.comboBox.itemData(self.comboBox.currentIndex(), Qt.UserRole))

        if self.optionsWidget:
            self.layout.removeWidget(self.optionsWidget)
            self.optionsWidget.setParent(None)
            self.optionsWidget.deleteLater()
        self.optionsWidget = None

        self.comboBox.clear()

        from ..competitions.competitionfactory import XkorCompetitionFactory

        competitionTypes = XkorCompetitionFactory.competitionTypes()
        for key, value in competitionTypes.items():
            if p.supportsCompetition(key):
                self.comboBox.insertItem(0, value, key)

        newIndex = self.comboBox.findData(currentCompetitionType, Qt.UserRole)
        if newIndex == -1:
            newIndex = self.comboBox.findData(p.defaultCompetition(), Qt.UserRole)
        if newIndex == -1:
            newIndex = 0  # pick the first format in the list if nothing useful is available
        self.comboBox.setCurrentIndex(newIndex)
        self.updateCompetition(newIndex)

    def updateCompetition(self, index):
        newComp = toString(self.comboBox.itemData(index))

        # update the competition in the event
        self.competitionChanged.emit(newComp)

        # check whether this competition has an options dialog
        try:
            from ..competitions.competitionfactory import XkorCompetitionFactory

            c = XkorCompetitionFactory.newCompetition(newComp)
        except ImportError:
            # the competitions package is being ported concurrently; once it is
            # complete this branch is unreachable
            return

        if self.optionsWidget:
            self.layout.removeWidget(self.optionsWidget)
            self.optionsWidget.setParent(None)
            self.optionsWidget.deleteLater()
        self.optionsWidget = None

        if c.hasOptionsWidget():
            self.optionsWidget = c.newOptionsWidget(self.currentOptions)
            self.layout.addWidget(self.optionsWidget, 2, 0, Qt.AlignTop)
            self.optionsWidget.optionsChanged.connect(self.updateCompetitionOptions)

    def updateCompetitionOptions(self, newOptions):
        self.currentOptions = newOptions
        self.competitionOptionsChanged.emit(newOptions)
