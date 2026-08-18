import time

from PySide6.QtCore import QDir, QSize, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QMessageBox, QPlainTextEdit, QStyle,
                               QToolBar, QVBoxLayout, QWidget)

from ..bbcode import boldWinners
from ..event import XkorEvent
from ..icons import icon_action
from ..rng import Mt19937
from ..rplist import XkorRPList
from ..signuplist import XkorSignupList
from ..sport import XkorSport
from ..startlist import XkorStartList
from ..ui.dialogs import message_box, resolved_search_path
from ..ui.fonts import monospace_font, widen_combo_popup
from ..ui.typography import heading_label


# Value-semantics helpers: these classes are passed by value in the C++ code,
# so we copy them at the call boundaries (see PORTING.md).

def _cloneSignupList(sl):
    rval = XkorSignupList()
    rval.ath = [a.clone() for a in sl.ath]
    rval.min = sl.min
    rval.max = sl.max
    return rval


def _cloneSport(s):
    rval = XkorSport()
    rval.m_name = s.m_name
    rval.m_alphaName = s.m_alphaName
    rval.m_discipline = s.m_discipline
    rval.m_event = s.m_event
    rval.m_scorinator = s.m_scorinator
    rval.m_paradigm = s.m_paradigm
    rval.m_paradigmOptions = dict(s.m_paradigmOptions)
    rval.m_dataPoints = {k: dict(v) for k, v in s.m_dataPoints.items()}
    rval.r = s.r
    return rval


def _cloneRPList(rp):
    rval = XkorRPList()
    rval.m_competitionName = rp.m_competitionName
    rval.bon = {k: dict(v) for k, v in rp.bon.items()}
    rval.rpCalcType = rp.rpCalcType
    rval.rpOpts = dict(rp.rpOpts)
    rval.max = rp.max
    rval.min = rp.min
    rval.eff = rp.eff
    rval.teams = rp.teams
    return rval


def _cloneEvent(e):
    rval = XkorEvent()
    rval.m_competition = e.m_competition
    rval.m_competitionOptions = dict(e.m_competitionOptions)
    rval.m_name = e.m_name
    rval.m_groups = [g.clone() for g in e.m_groups]
    rval.m_paradigm = e.m_paradigm
    rval.m_paradigmOptions = dict(e.m_paradigmOptions)
    rval.m_results = dict(e.m_results)
    rval.m_signupList = _cloneSignupList(e.m_signupList)
    rval.m_sport = e.m_sport
    return rval


class XkorScorinateWidget(QWidget):
    resultConfirmed = Signal(int, str)
    resultExportDirectoryChanged = Signal(str)
    resumeFileOptionsSet = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.c = None
        self.lastMatchday = -1

        self.r = Mt19937()
        self.r.seed(int(time.time()))
        self.dialog = None

        self.e = XkorEvent()
        self.rp = XkorRPList()
        self.s = XkorSport()
        self.sl = XkorStartList()

        # label
        label = heading_label("Scorinate event", level=1, center=True)

        # actions for scorinate widget buttons
        self.scorinateAction = icon_action("roll", "Scorinate event", self)
        self.scorinateAction.triggered.connect(self.scorinate)
        self.scorinateAction.triggered.connect(self.updateButtons)

        self.exportResultsAction = icon_action("document-export", "Export to file", self)
        self.exportResultsAction.setEnabled(False)
        self.exportResultsAction.triggered.connect(lambda: self.exportResults())

        self.oddsAction = icon_action("odds", "View match odds", self)
        self.oddsAction.setEnabled(False)
        self.oddsAction.triggered.connect(self.viewOdds)

        # toolbar
        toolBar = QToolBar()
        small = self.style().pixelMetric(QStyle.PM_SmallIconSize)
        toolBar.setIconSize(QSize(small, small))
        toolBar.addAction(self.scorinateAction)
        toolBar.addAction(self.oddsAction)
        toolBar.addAction(self.exportResultsAction)

        self.matchday = QComboBox()
        # repopulated whenever the competition changes, so AdjustToContents
        # keeps it sized to the current matchday names
        self.matchday.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.matchday.currentIndexChanged.connect(self.updateButtons)
        self.matchday.currentIndexChanged.connect(self.updateResults)

        self.bbcodeCheckBox = QCheckBox("BBCode output ([pre] tags, bold winners)")
        self.bbcodeCheckBox.toggled.connect(lambda: self.updateResults(self.matchday.currentIndex()))

        self.textedit = QPlainTextEdit()
        self.textedit.setReadOnly(True)
        self.textedit.setFont(monospace_font())

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(label, 0, Qt.AlignCenter)
        self.layout.addWidget(self.matchday, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.bbcodeCheckBox, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.textedit, 1)
        self.layout.addWidget(toolBar, 0, Qt.AlignCenter)

        self.layout.setContentsMargins(0, 0, 0, 0)

    def clear(self):
        self.e = XkorEvent()
        self.rp = XkorRPList()
        self.s = XkorSport()
        self.sl = XkorStartList()
        self.textedit.setPlainText("")
        self.matchday.clear()
        self.matchday.hide()
        self.oddsAction.setEnabled(False)

    def exportResults(self, filename=None):
        # C++ overloads: exportResults() shows the dialog; exportResults(QString) writes
        if filename is None:
            if not self.dialog:
                self.dialog = QFileDialog(self)
                self.dialog.setWindowTitle("Save results")
                self.dialog.setNameFilter("Text files (*.txt)")
                self.dialog.setDefaultSuffix("txt")
                self.dialog.setWindowModality(Qt.WindowModal)
                self.dialog.setAcceptMode(QFileDialog.AcceptSave)
                self.dialog.fileSelected.connect(self.exportResults)
            self.dialog.setDirectory(resolved_search_path("resultsExport"))
            self.dialog.open()
            return

        if filename != "":
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.textedit.document().toPlainText())

            path = QDir(filename)
            path.cdUp()  # go up from the file to the directory
            self.dialog.setDirectory(path)
            self.resultExportDirectoryChanged.emit(path.canonicalPath())

    def scorinate(self):
        if self.matchday.currentIndex() <= self.lastMatchday:
            if self.matchday.currentIndex() == self.lastMatchday:
                warning = message_box(
                    self, "Are you sure you want to regenerate %s?" % self.matchday.currentText(),
                    QMessageBox.Ok | QMessageBox.Cancel,
                    informativeText="You will lose your existing results for this round if you regenerate them.",
                    defaultButton=QMessageBox.Cancel, escapeButton=QMessageBox.Cancel)
                result = warning.exec()
            else:
                warning = message_box(
                    self, "Are you sure you want to regenerate %s and lose all subsequent results?"
                    % self.matchday.currentText(),
                    QMessageBox.Ok | QMessageBox.Cancel,
                    informativeText="You will lose your current results for %s through %s."
                    % (self.matchday.currentText(), self.matchday.itemText(self.lastMatchday)),
                    icon=QMessageBox.Warning,
                    defaultButton=QMessageBox.Cancel, escapeButton=QMessageBox.Cancel)
                result = warning.exec()
            if result == QMessageBox.Cancel:
                return
            else:
                # now that we’ve got permission, back up to the matchday we’re going to resim
                self.lastMatchday = self.matchday.currentIndex() - 1
                resumeOpts = self.c.revertToMatchday(self.matchday.currentIndex())
                self.updateCompetition(resumeOpts, self.lastMatchday, self.c.results(self.lastMatchday))

        if self.matchday.currentIndex() > 0 and self.c.results(self.matchday.currentIndex() - 1) == "":
            warning = message_box(
                self, "Do you want to generate results for %s through %s?"
                % (self.matchday.itemText(self.lastMatchday + 1), self.matchday.currentText()),
                QMessageBox.Ok | QMessageBox.Cancel,
                informativeText="This will generate %s rounds of results."
                % (self.matchday.currentIndex() - self.lastMatchday),
                defaultButton=QMessageBox.Cancel, escapeButton=QMessageBox.Cancel)
            result = warning.exec()
            if result == QMessageBox.Cancel:
                return

        for i in range(self.lastMatchday + 1, self.matchday.currentIndex() + 1):
            self.scorinateMatchday(i)

    def scorinateMatchday(self, md):
        # scorinate
        self.c.scorinate(md)
        self.updateResults(self.matchday.currentIndex())  # we should show the results for the selected matchday, not those we just scorinated

        # resume file
        resumeOpts = self.c.resumeFileOptions()
        self.lastMatchday = md

        # set resume file options
        self.resumeFileOptionsSet.emit(resumeOpts)
        self.resultConfirmed.emit(md, self.c.results(md))
        self.updateCompetition(resumeOpts, md, self.c.results(md))
        self.updateButtons()

    def setEvent(self, event, rpList, sport):
        # XkorEvent, XkorRPList and XkorSport are passed by value in the C++
        event = _cloneEvent(event)
        rpList = _cloneRPList(rpList)
        sport = _cloneSport(sport)

        sport.setPRNG(self.r)

        self.e = event
        self.rp = rpList
        self.s = sport

        # create the list of participants
        self.sl = event.makeStartList(rpList)

        # create the competition
        from ..competitions.competitionfactory import XkorCompetitionFactory

        self.c = XkorCompetitionFactory.newCompetitionFull(
            event.competition(), self.sl, sport, event.paradigmOptions(),
            event.competitionOptions(), event.results())

        self.matchday.clear()
        matchdayNames = self.c.matchdayNames()
        for i in range(len(matchdayNames)):
            self.matchday.insertItem(i, matchdayNames[i])
        widen_combo_popup(self.matchday)
        if len(matchdayNames) <= 1:
            self.matchday.hide()
        else:
            self.matchday.show()

        self.oddsAction.setEnabled(self.c.supportsOdds())

        self.lastMatchday = -1
        for i in range(len(matchdayNames)):
            if self.c.results(i) != "":
                self.lastMatchday = i

    def updateButtons(self):
        if self.e.results().get(self.matchday.currentIndex(), "") == "":
            self.exportResultsAction.setEnabled(False)
        else:
            self.exportResultsAction.setEnabled(True)

    def updateCompetition(self, resumeFileOptions, matchday, result):
        self.e.replaceCompetitionOptions(resumeFileOptions)
        self.e.setResult(matchday, result)

        from ..competitions.competitionfactory import XkorCompetitionFactory

        self.c = XkorCompetitionFactory.newCompetitionFull(
            self.e.competition(), self.sl, self.s, self.e.paradigmOptions(),
            self.e.competitionOptions(), self.e.results())

    def updateResults(self, matchday):
        self.textedit.setPlainText(self._formatResults(self.c.results(matchday)))

    def viewOdds(self):
        if self.c is None:
            return
        odds = self.c.matchOdds(self.matchday.currentIndex())
        if odds is None:
            return
        self._showTextPreview("Match odds — %s" % self.matchday.currentText(), odds)

    def _showTextPreview(self, title, text):
        # shown in its own dialog, never in self.textedit — that widget is
        # the results view, and overwriting it left users with no way back
        # to their actual scores short of reopening the event
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.resize(560, 420)

        preview = QPlainTextEdit(self._formatResults(text))
        preview.setReadOnly(True)
        preview.setFont(monospace_font())

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)

        layout = QVBoxLayout(dialog)
        layout.addWidget(preview, 1)
        layout.addWidget(buttons)

        dialog.exec()

    def _formatResults(self, text):
        if self.bbcodeCheckBox.isChecked() and text != "":
            return "[pre]%s[/pre]" % boldWinners(text)
        return text
