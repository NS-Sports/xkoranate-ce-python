import math

from PySide6.QtCore import QDir, QFileInfo, QRegularExpression, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGridLayout, QLabel, QMessageBox,
                               QPlainTextEdit, QSpinBox, QWidget)

from ..ui.dialogs import message_box, resolved_search_path
from ..ui.fonts import monospace_font
from ..variant import toDouble, toString
from .sortcriteriawidget import XkorSortCriteriaWidget
from .table import XkorTable
from .tablecolumn import XkorTableColumn
from .tablematch import XkorTableMatch


def _qLeft(s, n):
    # QString::left(n): the entire string is returned if n >= size() or n < 0
    if n < 0 or n >= len(s):
        return s
    return s[:n]


def _qRight(s, n):
    # QString::right(n): the entire string is returned if n >= size() or n < 0
    if n < 0 or n >= len(s):
        return s
    return s[len(s) - n:]


class XkorTableGenerator(QWidget):
    fileChanged = Signal(str)  # loaded a new file
    fileEdited = Signal(bool)  # changed the current file
    resultImportDirectoryChanged = Signal(str)
    tableDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.t = XkorTable()
        self.matchesList = []
        self.teamsList = []
        self.currentFileName = ""
        self.fileModified = False
        self.matchesModified = False

        self.dialog = QFileDialog(self, "Save table file", resolved_search_path("tables"),
                                  "XML files (*.xml)")
        self.dialog.setWindowModality(Qt.WindowModal)
        self.dialog.setDefaultSuffix("xml")

        self.importDialog = QFileDialog(self, "Import results file",
                                        resolved_search_path("resultsImport"), "Text files (*.txt)")
        self.importDialog.setWindowModality(Qt.WindowModal)
        self.importDialog.setAcceptMode(QFileDialog.AcceptOpen)

        self.pointsForWin = QSpinBox()
        self.pointsForWin.valueChanged.connect(lambda: self.setFileModified())
        self.pointsForDraw = QSpinBox()
        self.pointsForDraw.valueChanged.connect(lambda: self.setFileModified())
        self.pointsForLoss = QSpinBox()
        self.pointsForLoss.valueChanged.connect(lambda: self.setFileModified())
        self.pointsForOTWin = QSpinBox()
        self.pointsForOTWin.valueChanged.connect(lambda: self.setFileModified())
        self.pointsForSOWin = QSpinBox()
        self.pointsForSOWin.valueChanged.connect(lambda: self.setFileModified())
        self.pointsForOTLoss = QSpinBox()
        self.pointsForOTLoss.valueChanged.connect(lambda: self.setFileModified())
        self.pointsForSOLoss = QSpinBox()
        self.pointsForSOLoss.valueChanged.connect(lambda: self.setFileModified())
        self.columnWidth = QSpinBox()
        self.columnWidth.valueChanged.connect(lambda: self.setFileModified())

        self.scw = XkorSortCriteriaWidget()
        self.scw.listChanged.connect(lambda: self.setFileModified())

        self.showDraws = QCheckBox("Draws")
        self.showDraws.stateChanged.connect(lambda: self.setFileModified())
        self.showOvertime = QCheckBox("OT/SO breakdown (OTW/SOW/OTL/SOL)")
        self.showOvertime.stateChanged.connect(lambda: self.setFileModified())
        self.showResultsGrid = QCheckBox("Results grid")
        self.showResultsGrid.stateChanged.connect(lambda: self.setFileModified())

        self.goalName = QComboBox()
        self.goalName.addItem("Goals (G)", "G")
        self.goalName.addItem("Korfs (K)", "K")
        self.goalName.addItem("Points (P)", "P")
        self.goalName.addItem("Runs (R)", "R")
        self.goalName.currentIndexChanged.connect(lambda: self.setFileModified())

        self.matches = QPlainTextEdit()
        self.matches.textChanged.connect(lambda: self.setFileModified())
        self.matches.textChanged.connect(self.setMatchesModified)

        self.table = QPlainTextEdit()
        self.table.setFont(monospace_font())
        self.table.setReadOnly(True)

        pointsLayout = QGridLayout()
        pointsLayout.addWidget(self.pointsForWin, 0, 0)
        pointsLayout.addWidget(QLabel("Draw:"), 0, 1)
        pointsLayout.addWidget(self.pointsForDraw, 0, 2)
        pointsLayout.addWidget(QLabel("Loss:"), 0, 3)
        pointsLayout.addWidget(self.pointsForLoss, 0, 4)
        pointsLayout.setContentsMargins(0, 0, 0, 0)
        pointsLayout.setColumnStretch(0, 1)
        pointsLayout.setColumnStretch(1, 0)  # don't stretch the labels
        pointsLayout.setColumnStretch(2, 1)
        pointsLayout.setColumnStretch(3, 0)  # don't stretch the labels
        pointsLayout.setColumnStretch(4, 1)

        otPointsLayout = QGridLayout()
        otPointsLayout.addWidget(self.pointsForOTWin, 0, 0)
        otPointsLayout.addWidget(QLabel("OT loss:"), 0, 1)
        otPointsLayout.addWidget(self.pointsForOTLoss, 0, 2)
        otPointsLayout.setContentsMargins(0, 0, 0, 0)

        soPointsLayout = QGridLayout()
        soPointsLayout.addWidget(self.pointsForSOWin, 0, 0)
        soPointsLayout.addWidget(QLabel("SO loss:"), 0, 1)
        soPointsLayout.addWidget(self.pointsForSOLoss, 0, 2)
        soPointsLayout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.addRow("Table sort rules:", self.scw)
        form.addRow("Points for win:", pointsLayout)
        form.addRow("Points for OT win:", otPointsLayout)
        form.addRow("Points for SO win:", soPointsLayout)
        form.addRow("Show columns:", self.showDraws)
        form.addRow("", self.showOvertime)
        form.addRow("", self.showResultsGrid)
        form.addRow("Goals are called:", self.goalName)
        form.addRow("Column width:", self.columnWidth)

        matchResultsLabel = QLabel("Match results:")

        layout = QGridLayout(self)
        layout.addWidget(matchResultsLabel, 0, 0, Qt.AlignTop)
        layout.addWidget(self.matches, 0, 1)
        layout.addLayout(form, 0, 2)
        layout.addWidget(self.table, 1, 0, 1, 3)  # rowspan = 3

        self.setFileModified(False)
        self.reset()

    def _openDialog(self, dialog, slot):
        # mimics QFileDialog::open(receiver, member): connect fileSelected to
        # the slot, show the dialog, disconnect when it closes
        dialog.fileSelected.connect(slot)

        def disconnectOnClose():
            dialog.fileSelected.disconnect(slot)
            dialog.finished.disconnect(disconnectOnClose)

        dialog.finished.connect(disconnectOnClose)
        dialog.open()

    def closeEvent(self, event):
        if self.okayToLoad():
            QWidget.closeEvent(self, event)
        else:
            event.ignore()

    def generateMatches(self):
        self.matchesList = []
        self.teamsList = []

        text = self.matches.toPlainText()

        for line in text.split("\n"):
            # match scores of form Aquilla 3–1 Busby, with en dash,
            # hyphen-minus, or colon as delimiter, and an optional trailing
            # "OT" or "SO" marker for matches decided in overtime/extra time
            # or by shootout/penalties, e.g. Aquilla 3–2 OT Busby
            rx = QRegularExpression("([0-9]+)[-–:]([0-9]+)(?:\\s+(OT|SO))?")
            match = rx.match(line)
            if match.hasMatch():  # if we matched
                index = match.capturedStart(0)
                matchedLength = match.capturedLength(0)
                homeTeam = _qLeft(line, index - 1)
                awayTeam = _qRight(line, len(line) - index - matchedLength - 1)
                homeScore = toDouble(match.captured(1))
                awayScore = toDouble(match.captured(2))
                decider = match.captured(3) or None
                self.matchesList.append(
                    XkorTableMatch(homeTeam, awayTeam, homeScore, awayScore, decider))
                if homeTeam not in self.teamsList:
                    self.teamsList.append(homeTeam)
                if awayTeam not in self.teamsList:
                    self.teamsList.append(awayTeam)

    def generateTable(self):
        self.updateTable()
        self.t.generate()
        self.table.setPlainText(self.t.toText())
        self.matchesModified = False

    def generateTableColumns(self):
        columns = []

        nameWidth = 20
        for i in self.teamsList:
            if len(i) > nameWidth:
                nameWidth = len(i)
        matchdayWidth = self.columnWidth.value()
        teams = len(self.teamsList)
        # C++: int positionWidth = log10(teams) + 1; log10(0) is undefined
        # behaviour there — guard against it here
        positionWidth = int(math.log10(teams) + 1) if teams > 0 else 1
        chosenGoalName = toString(
            self.goalName.itemData(self.goalName.currentIndex()))

        sortCriteria = self.scw.sortCriteria()
        usesGoalAverage = "goalAverage" in sortCriteria
        usesGoalDifference = "goalDifference" in sortCriteria
        usesGoalsAgainst = "goalsAgainst" in sortCriteria
        usesGoalsFor = "goalsFor" in sortCriteria
        usesWinPercent = "winPercent" in sortCriteria
        usesWinPercentPure = "winPercentPure" in sortCriteria
        usesWinPercentNFL = "winPercentNFL" in sortCriteria
        usesPoints = "points" in sortCriteria

        columns.append(XkorTableColumn("position", "", positionWidth))
        columns.append(XkorTableColumn("name", "", nameWidth))
        columns.append(XkorTableColumn("played", "Pld", matchdayWidth + 2))
        columns.append(XkorTableColumn("wins", "W", matchdayWidth + 2))
        if self.showDraws.checkState() == Qt.Checked:
            columns.append(XkorTableColumn("draws", "D", matchdayWidth + 1))
        columns.append(XkorTableColumn("losses", "L", matchdayWidth + 1))
        if self.showOvertime.checkState() == Qt.Checked:
            columns.append(XkorTableColumn("otWins", "OTW", matchdayWidth + 2))
            columns.append(XkorTableColumn("soWins", "SOW", matchdayWidth + 2))
            columns.append(XkorTableColumn("otLosses", "OTL", matchdayWidth + 2))
            columns.append(XkorTableColumn("soLosses", "SOL", matchdayWidth + 2))
        if usesGoalAverage or usesGoalDifference or usesGoalsAgainst or usesGoalsFor:
            columns.append(XkorTableColumn("goalsFor", chosenGoalName + "F",
                                           matchdayWidth + 3))
            columns.append(XkorTableColumn("goalsAgainst", chosenGoalName + "A",
                                           matchdayWidth + 2))
        if usesGoalAverage:
            columns.append(XkorTableColumn("goalAverage", "Avg", 7))
        if usesGoalDifference:
            columns.append(XkorTableColumn("goalDifference",
                                           chosenGoalName + "D",
                                           matchdayWidth + 2))
        if usesWinPercent:
            columns.append(XkorTableColumn("winPercent", "Win %", 8))
        if usesWinPercentPure:
            columns.append(XkorTableColumn("winPercentPure", "Win %", 8))
        if usesWinPercentNFL:
            columns.append(XkorTableColumn("winPercentNFL", "Win %", 8))
        if usesPoints:
            columns.append(XkorTableColumn("points", "Pts", matchdayWidth + 3))
        if self.showResultsGrid.checkState() == Qt.Checked:
            columns.append(XkorTableColumn("resultsGrid", "", teams * 5))

        return columns

    def importResults(self, filename=None):
        if filename is None:
            self.importDialog.setDirectory(resolved_search_path("resultsImport"))
            self._openDialog(self.importDialog, self.importResults)
            return

        with open(filename, "rb") as f:
            data = f.read()
        self.matches.appendPlainText(data.decode("utf-8", errors="replace"))
        self.generateTable()

        path = QDir(filename)
        path.cdUp()
        self.resultImportDirectoryChanged.emit(path.canonicalPath())

    def okayToLoad(self):
        if self.fileModified:
            r = self.showUnsavedDialog()
            if r == QMessageBox.Cancel:
                return False
        return True  # if the current file hasn't been modified, or if the user clicked Yes or No

    def openFile(self, filename=None):
        if filename is None:
            if self.okayToLoad():
                self.dialog.setAcceptMode(QFileDialog.AcceptOpen)
                self.dialog.setDirectory(resolved_search_path("tables"))
                self._openDialog(self.dialog, self.openFile)
            return

        from ..xml.xmltablereader import XkorXmlTableReader
        r = XkorXmlTableReader(filename)
        if r.hasError():
            QMessageBox.critical(self, "xkoranate", r.error())
        else:
            self.t = r.table()

            self.matches.setPlainText(r.matches())
            self.pointsForWin.setValue(self.t.getPointsForWin())
            self.pointsForDraw.setValue(self.t.getPointsForDraw())
            self.pointsForLoss.setValue(self.t.getPointsForLoss())
            self.pointsForOTWin.setValue(self.t.getPointsForOTWin())
            self.pointsForSOWin.setValue(self.t.getPointsForSOWin())
            self.pointsForOTLoss.setValue(self.t.getPointsForOTLoss())
            self.pointsForSOLoss.setValue(self.t.getPointsForSOLoss())
            self.columnWidth.setValue(self.t.getColumnWidth())
            self.scw.setSortCriteria(self.t.getSortCriteria())
            self.showDraws.setCheckState(
                Qt.Checked if self.t.getShowDraws() else Qt.Unchecked)
            self.showOvertime.setCheckState(
                Qt.Checked if self.t.getShowOvertime() else Qt.Unchecked)
            self.showResultsGrid.setCheckState(
                Qt.Checked if self.t.getShowResultsGrid() else Qt.Unchecked)
            self.goalName.setCurrentIndex(
                self.goalName.findData(self.t.getGoalName()))

            self.generateTable()

            self.currentFileName = filename
            self.fileChanged.emit(filename)
            self.setFileModified(False)

            path = QDir(filename)
            path.cdUp()
            self.tableDirectoryChanged.emit(path.canonicalPath())

    def reset(self):
        if self.okayToLoad():
            self.t = XkorTable()
            self.matches.setPlainText("")
            self.pointsForWin.setValue(3)
            self.pointsForDraw.setValue(1)
            self.pointsForLoss.setValue(0)
            self.pointsForOTWin.setValue(3)
            self.pointsForSOWin.setValue(3)
            self.pointsForOTLoss.setValue(0)
            self.pointsForSOLoss.setValue(0)
            self.columnWidth.setValue(2)
            self.scw.setSortCriteria(self.scw.defaultSortCriteria())
            self.showDraws.setCheckState(Qt.Checked)
            self.showOvertime.setCheckState(Qt.Unchecked)
            self.showResultsGrid.setCheckState(Qt.Unchecked)
            self.goalName.setCurrentIndex(self.goalName.findData("G"))

            self.table.setPlainText("")

            self.matchesList = []
            self.teamsList = []
            self.matchesModified = False

            self.currentFileName = ""
            self.fileChanged.emit("")
            self.setFileModified(False)

    def saveFile(self, filename=""):
        if not filename:  # if no filename was specified
            if not self.currentFileName:  # still "Untitled"?
                self.saveFileAs()
            else:
                filename = self.currentFileName

        self.updateTable()
        from ..xml.xmltablewriter import XkorXmlTableWriter
        w = XkorXmlTableWriter(filename, self.t)

        self.currentFileName = filename
        self.fileChanged.emit(filename)
        self.setFileModified(False)

        path = QDir(filename)
        path.cdUp()
        self.tableDirectoryChanged.emit(path.canonicalPath())

    def saveFileAs(self):
        self.dialog.setAcceptMode(QFileDialog.AcceptSave)
        self.dialog.setDirectory(resolved_search_path("tables"))
        self._openDialog(self.dialog, self.saveFile)

    def setFileModified(self, isEdited=True):
        self.fileModified = isEdited
        self.fileEdited.emit(isEdited)

    def setMatchesModified(self):
        self.matchesModified = True

    def showUnsavedDialog(self):
        displayFileName = ("untitled" if not self.currentFileName
                           else QFileInfo(self.currentFileName).fileName())
        warning = message_box(
            self, "Do you want to save the changes you made to “%s”?" % displayFileName,
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            informativeText="Your changes will be lost if you don’t save them.",
            destructiveButton=QMessageBox.Discard)
        return warning.exec()

    def updateTable(self):
        if self.matchesModified:
            self.generateMatches()
        self.t.setColumns(self.generateTableColumns())
        self.t.setMatches(self.matchesList)
        self.t.setPointsForWin(self.pointsForWin.value())
        self.t.setPointsForDraw(self.pointsForDraw.value())
        self.t.setPointsForLoss(self.pointsForLoss.value())
        self.t.setPointsForOTWin(self.pointsForOTWin.value())
        self.t.setPointsForSOWin(self.pointsForSOWin.value())
        self.t.setPointsForOTLoss(self.pointsForOTLoss.value())
        self.t.setPointsForSOLoss(self.pointsForSOLoss.value())
        self.t.setSortCriteria(self.scw.sortCriteria())
        self.t.setColumnWidth(self.columnWidth.value())
        self.t.setGoalName(toString(
            self.goalName.itemData(self.goalName.currentIndex())))
        self.t.setShowDraws(self.showDraws.checkState() == Qt.Checked)
        self.t.setShowOvertime(self.showOvertime.checkState() == Qt.Checked)
        self.t.setShowResultsGrid(self.showResultsGrid.checkState() == Qt.Checked)
