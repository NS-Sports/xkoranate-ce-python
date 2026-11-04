from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGridLayout, QLabel, QSpinBox

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toBool, toInt, toList, toString


class XkorRoundRobinCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        from xkoranate.competitions.roundrobincompetition import tablePoints
        from xkoranate.tablegenerator.sortcriteriawidget import XkorSortCriteriaWidget

        # set up basic options
        draws = toBool(self.options.get("allowDraws", True))
        legs = toInt(self.options.get("numberOfLegs", 1))
        grid = toBool(self.options.get("showResultsGrid", False))

        self.numberOfLegs = QSpinBox()
        self.numberOfLegs.setValue(legs)
        self.numberOfLegs.setMinimum(1)
        self.numberOfLegs.setMaximum(99999)
        self.setNumberOfLegs(self.numberOfLegs.value())
        self.numberOfLegs.valueChanged.connect(self.setNumberOfLegs)
        self.numberOfLegs.valueChanged.connect(self.checkResultsGridUsability)

        self.allowDraws = QCheckBox("Allow draws")
        self.allowDraws.setChecked(draws)
        self.allowDraws.stateChanged.connect(self.setAllowDraws)

        # set up table options
        pointsForWin, pointsForDraw, pointsForLoss = tablePoints(self.options)

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

        self.ptsWin = QSpinBox()
        self.ptsWin.setValue(pointsForWin)
        self.ptsWin.valueChanged.connect(self.setPointsForWin)

        self.ptsDraw = QSpinBox()
        self.ptsDraw.setValue(pointsForDraw)
        self.ptsDraw.valueChanged.connect(self.setPointsForDraw)

        self.ptsLoss = QSpinBox()
        self.ptsLoss.setValue(pointsForLoss)
        self.ptsLoss.valueChanged.connect(self.setPointsForLoss)

        self.showResultsGrid = QCheckBox("Show results grid")
        self.showResultsGrid.setChecked(grid)
        self.checkResultsGridUsability(legs)
        self.showResultsGrid.stateChanged.connect(self.setShowResultsGrid)

        # layout
        pointsLayout = QGridLayout()
        pointsLayout.addWidget(self.ptsWin, 0, 0)
        pointsLayout.addWidget(QLabel("Draw:"), 0, 1)
        pointsLayout.addWidget(self.ptsDraw, 0, 2)
        pointsLayout.addWidget(QLabel("Loss:"), 0, 3)
        pointsLayout.addWidget(self.ptsLoss, 0, 4)
        pointsLayout.setContentsMargins(0, 0, 0, 0)
        pointsLayout.setColumnStretch(0, 1)
        pointsLayout.setColumnStretch(1, 0)  # don’t stretch the labels
        pointsLayout.setColumnStretch(2, 1)
        pointsLayout.setColumnStretch(3, 0)  # don’t stretch the labels
        pointsLayout.setColumnStretch(4, 1)

        layout = QFormLayout(self)
        layout.addRow("Number of legs:", self.numberOfLegs)
        layout.addRow("", self.allowDraws)
        layout.addRow("", self.showResultsGrid)
        layout.addRow("Table sort rules:", self.sc)
        layout.addRow("Points for win:", pointsLayout)

    def checkResultsGridUsability(self, legs):
        # we want to preserve the state of the check box even if it’s disabled, but we don’t want the results grid to actually be shown if it should be disabled
        if legs == 2:
            self.showResultsGrid.setEnabled(True)
            self.options["showResultsGrid"] = (self.showResultsGrid.checkState() == Qt.CheckState.Checked)
        else:
            self.showResultsGrid.setEnabled(False)
            self.options["showResultsGrid"] = "false"

    def setAllowDraws(self, value):
        if isinstance(value, Qt.CheckState):
            value = value.value
        if value == Qt.CheckState.Checked.value:
            self.options["allowDraws"] = "true"
        else:
            self.options["allowDraws"] = "false"
        self.optionsChanged.emit(self.options)

    def setNumberOfLegs(self, value):
        self.options["numberOfLegs"] = str(value)
        self.optionsChanged.emit(self.options)

    def setPointsForDraw(self, value):
        self.options["pointsForDraw"] = str(value)
        self.optionsChanged.emit(self.options)

    def setPointsForLoss(self, value):
        self.options["pointsForLoss"] = str(value)
        self.optionsChanged.emit(self.options)

    def setPointsForWin(self, value):
        self.options["pointsForWin"] = str(value)
        self.optionsChanged.emit(self.options)

    def setShowResultsGrid(self, value):
        if isinstance(value, Qt.CheckState):
            value = value.value
        if value == Qt.CheckState.Checked.value:
            self.options["showResultsGrid"] = "true"
        else:
            self.options["showResultsGrid"] = "false"
        self.optionsChanged.emit(self.options)

    def setSortCriteria(self):
        sortCriteria = []
        criteriaVector = self.sc.sortCriteria()
        for i in criteriaVector:
            sortCriteria.append(i)
        self.options["sortCriteria"] = sortCriteria
        self.optionsChanged.emit(self.options)
