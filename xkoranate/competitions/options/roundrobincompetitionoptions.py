from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QSpinBox

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toBool, toInt, toList, toString


class XkorRoundRobinCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        from xkoranate.competitions.roundrobincompetition import DEFAULT_POINTS, tablePoints
        from xkoranate.tablegenerator.pointsrow import pointsRowLayout
        from xkoranate.tablegenerator.sortcriteriawidget import XkorSortCriteriaWidget

        # set up basic options
        draws = toBool(self.options.get("allowDraws", True))
        legs = toInt(self.options.get("numberOfLegs", 1))
        grid = toBool(self.options.get("showResultsGrid", False))

        self.numberOfLegs = QSpinBox()
        self.numberOfLegs.setValue(legs)
        self.numberOfLegs.setMinimum(1)
        self.numberOfLegs.setMaximum(99999)
        self._setOption("numberOfLegs", str(self.numberOfLegs.value()))
        self.numberOfLegs.valueChanged.connect(lambda value: self._setOption("numberOfLegs", str(value)))
        self.numberOfLegs.valueChanged.connect(self.checkResultsGridUsability)

        self.allowDraws = self._flagCheckBox("allowDraws", "Allow draws", draws, storeNow=False)

        # set up table options
        if "sortCriteria" in self.options:
            sortCriteria = []
            oldCriteria = toList(self.options.get("sortCriteria"))
            for i in oldCriteria:
                sortCriteria.append(toString(i))
        else:
            sortCriteria = XkorSortCriteriaWidget.defaultSortCriteria()

        self.sc = XkorSortCriteriaWidget()
        self.sc.setSortCriteria(sortCriteria)
        self.sc.listChanged.connect(self.setSortCriteria)

        self.ptsWin, self.ptsDraw, self.ptsLoss = QSpinBox(), QSpinBox(), QSpinBox()
        for box, (key, _default), value in zip((self.ptsWin, self.ptsDraw, self.ptsLoss), DEFAULT_POINTS,
                                               tablePoints(self.options)):
            box.setValue(value)
            box.valueChanged.connect(lambda value, key=key: self._setOption(key, str(value)))

        self.showResultsGrid = self._flagCheckBox("showResultsGrid", "Show results grid", grid,
                                                  storeNow=False)
        self.checkResultsGridUsability(legs)

        # layout
        layout = QFormLayout(self)
        layout.addRow("Number of legs:", self.numberOfLegs)
        layout.addRow("", self.allowDraws)
        layout.addRow("", self.showResultsGrid)
        layout.addRow("Table sort rules:", self.sc)
        layout.addRow("Points for win:", pointsRowLayout(self.ptsWin, self.ptsDraw, self.ptsLoss))

    def checkResultsGridUsability(self, legs):
        # we want to preserve the state of the check box even if it’s disabled, but we don’t want the results grid to actually be shown if it should be disabled
        if legs == 2:
            self.showResultsGrid.setEnabled(True)
            self.options["showResultsGrid"] = (self.showResultsGrid.checkState() == Qt.CheckState.Checked)
        else:
            self.showResultsGrid.setEnabled(False)
            self.options["showResultsGrid"] = "false"

    def setSortCriteria(self):
        self._setOption("sortCriteria", list(self.sc.sortCriteria()))
