from PySide6.QtWidgets import QSpinBox

from xkoranate.competitions.options.roundrobincompetitionoptions import XkorRoundRobinCompetitionOptions
from xkoranate.tablegenerator.pointsrow import pointsRowLayout
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
        self._setOption("interConferenceLegs", str(self.interConferenceLegs.value()))
        self.interConferenceLegs.valueChanged.connect(
            lambda value: self._setOption("interConferenceLegs", str(value)))

        self.showOverallTable = self._flagCheckBox(
            "showOverallTable", "Overall table", toBool(self.options.get("showOverallTable", True)),
            storeNow=False)
        self.showOverallTable.setToolTip(
            "After the conference tables, also rank every team in one combined table.")

        layout.insertRow(1, "Legs v others:", self.interConferenceLegs)
        layout.insertRow(3, "", self.showOverallTable)

        # points: the round-robin row scores games within a conference, and
        # a second row scores games against other conferences. Until that
        # row is edited it follows the first, and nothing is saved for it,
        # so every game scores alike.
        layout.labelForField(self._pointsRow()).setText("Win in conf.:")
        for box in (self.ptsWin, self.ptsDraw, self.ptsLoss):
            box.setToolTip("Points for a win, draw or loss against a team in the same conference.")

        crossKeys = ("crossPointsForWin", "crossPointsForDraw", "crossPointsForLoss")
        self.crossFollows = not any(k in self.options for k in crossKeys)
        own = (self.ptsWin.value(), self.ptsDraw.value(), self.ptsLoss.value())
        self.crossWin, self.crossDraw, self.crossLoss = QSpinBox(), QSpinBox(), QSpinBox()
        for box, key, ownValue in zip((self.crossWin, self.crossDraw, self.crossLoss), crossKeys, own):
            box.setValue(toInt(self.options.get(key, ownValue)))
            box.setToolTip("Points for a win, draw or loss against a team in another conference. "
                           "Matches the row above until you change it.")
            box.valueChanged.connect(self.setCrossPoints)
        layout.addRow("Win v others:", pointsRowLayout(self.crossWin, self.crossDraw, self.crossLoss))

        for box in (self.ptsWin, self.ptsDraw, self.ptsLoss):
            box.valueChanged.connect(self.followOwnPoints)

    def _pointsRow(self):
        layout = self.layout()
        return layout.itemAt(layout.rowCount() - 1, layout.ItemRole.FieldRole).layout()

    def followOwnPoints(self):
        if not self.crossFollows:
            return
        for box, own in ((self.crossWin, self.ptsWin), (self.crossDraw, self.ptsDraw), (self.crossLoss, self.ptsLoss)):
            box.blockSignals(True)
            box.setValue(own.value())
            box.blockSignals(False)

    def setCrossPoints(self):
        self.crossFollows = False
        self.options["crossPointsForWin"] = str(self.crossWin.value())
        self.options["crossPointsForDraw"] = str(self.crossDraw.value())
        self.options["crossPointsForLoss"] = str(self.crossLoss.value())
        self.optionsChanged.emit(self.options)

    def checkResultsGridUsability(self, legs):
        self.showResultsGrid.setEnabled(False)
        self.options["showResultsGrid"] = "false"

