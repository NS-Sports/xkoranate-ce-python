from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QSpinBox

from xkoranate.competitions.options.roundrobincompetitionoptions import XkorRoundRobinCompetitionOptions
from xkoranate.variant import toBool, toInt


class XkorInterConferenceCompetitionOptions(XkorRoundRobinCompetitionOptions):
    """Round-robin options, plus how often conferences play each other."""

    def __init__(self, opts, parent=None):
        opts = dict(opts)
        # by default teams meet home and away within their conference
        opts.setdefault("numberOfLegs", "2")
        super().__init__(opts, parent)

        layout = self.layout()

        layout.labelForField(self.numberOfLegs).setText("Legs in conference:")
        self.numberOfLegs.setMinimum(0)
        self.numberOfLegs.setToolTip(
            "How many times each team plays every other team in its own conference. "
            "Each group is one conference.")

        # a conference table can't hold a grid against teams outside it
        layout.setRowVisible(self.showResultsGrid, False)

        otherLegs = toInt(self.options.get("interConferenceLegs", 1))
        self.interConferenceLegs = QSpinBox()
        self.interConferenceLegs.setMinimum(0)
        self.interConferenceLegs.setMaximum(99)
        self.interConferenceLegs.setValue(otherLegs)
        self.interConferenceLegs.setToolTip(
            "How many times each team plays every team in each other conference. "
            "0 keeps the conferences apart.")
        self.setInterConferenceLegs(self.interConferenceLegs.value())
        self.interConferenceLegs.valueChanged.connect(self.setInterConferenceLegs)

        self.showOverallTable = QCheckBox("Overall table")
        self.showOverallTable.setChecked(toBool(self.options.get("showOverallTable", True)))
        self.showOverallTable.setToolTip(
            "After the conference tables, also rank every team in one combined table.")
        self.showOverallTable.stateChanged.connect(self.setShowOverallTable)

        layout.insertRow(1, "Legs v others:", self.interConferenceLegs)
        layout.insertRow(3, "", self.showOverallTable)

    def checkResultsGridUsability(self, legs):
        self.showResultsGrid.setEnabled(False)
        self.options["showResultsGrid"] = "false"

    def setInterConferenceLegs(self, value):
        self.options["interConferenceLegs"] = str(value)
        self.optionsChanged.emit(self.options)

    def setShowOverallTable(self, value):
        if isinstance(value, Qt.CheckState):
            value = value.value
        self.options["showOverallTable"] = "true" if value == Qt.CheckState.Checked.value else "false"
        self.optionsChanged.emit(self.options)
