import sys
import time
import traceback

from PySide6.QtCore import QDir, QSize, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QSpinBox, QStyle,
                               QToolBar, QVBoxLayout, QWidget)

from ..bbcode import boldWinners
from ..competitions.qualification import (MODE_OFF, MODE_TOP,
                                          MODE_TOP_PLUS_BEST,
                                          QualificationSettings, ordinal)
from ..event import XkorEvent
from ..icons import icon_action
from ..rng import Mt19937
from ..rplist import XkorRPList
from ..signuplist import XkorSignupList
from ..sport import XkorSport
from ..startlist import XkorStartList
from ..ui.dialogs import message_box, resolved_search_path
from ..ui.fonts import monospace_font, widen_combo_popup
from ..ui.tooltips import wrapped_tooltip
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

        self.initQualificationBox()

        self.textedit = QPlainTextEdit()
        self.textedit.setReadOnly(True)
        self.textedit.setFont(monospace_font())

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(label, 0, Qt.AlignCenter)
        self.layout.addWidget(self.matchday, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.bbcodeCheckBox, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.qualificationBox, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.textedit, 1)
        self.layout.addWidget(toolBar, 0, Qt.AlignCenter)

        self.layout.setContentsMargins(0, 0, 0, 0)

    def initQualificationBox(self):
        # "Top [2] in each group  [ ] + best [1] 3rd-placed": one short row,
        # the explanations in tooltips (the window starts small)
        self.qualificationBox = QGroupBox("Format qualifications")
        self.qualificationBox.setCheckable(True)
        self.qualificationBox.setChecked(False)
        self.qualificationBox.setToolTip(wrapped_tooltip(
            "Mark who has mathematically qualified with Q and who has been "
            "eliminated with E, in a column after the points. Only the first "
            "sort rule (usually points) can be projected ahead, so a tie on "
            "it counts against the team: a marker appears only once no "
            "remaining result can change it."))

        self.qualificationPlaces = QSpinBox()
        self.qualificationPlaces.setRange(1, 999)
        self.qualificationPlaces.setValue(2)

        self.qualificationPerGroup = QLabel("in each group")

        self.qualificationBest = QCheckBox("+ best")
        self.qualificationBest.setToolTip(wrapped_tooltip(
            "Also qualify the best few who finish one place below the cut, "
            "compared across groups with the table's sort rules (head-to-head "
            "rules left out, as they never met)."))

        self.qualificationBestOf = QSpinBox()
        self.qualificationBestOf.setRange(1, 999)
        self.qualificationBestOf.setValue(1)

        self.qualificationBestLabel = QLabel()

        row = QHBoxLayout(self.qualificationBox)
        row.addWidget(QLabel("Top"))
        row.addWidget(self.qualificationPlaces)
        row.addWidget(self.qualificationPerGroup)
        row.addSpacing(8)
        row.addWidget(self.qualificationBest)
        row.addWidget(self.qualificationBestOf)
        row.addWidget(self.qualificationBestLabel)

        self.qualificationBox.toggled.connect(self.qualificationChanged)
        self.qualificationPlaces.valueChanged.connect(self.qualificationChanged)
        self.qualificationBest.toggled.connect(self.qualificationChanged)
        self.qualificationBestOf.valueChanged.connect(self.qualificationChanged)

        self.updateQualificationControls()
        self.qualificationBox.hide()  # until an event that supports it is shown

    def qualificationSettings(self):
        """The rule as the controls set it. "+ best" is kept even while it's
        hidden for a one-group event; the competition only applies it when
        there are groups to compare."""
        if not self.qualificationBox.isChecked():
            mode = MODE_OFF
        elif self.qualificationBest.isChecked():
            mode = MODE_TOP_PLUS_BEST
        else:
            mode = MODE_TOP
        return QualificationSettings(mode, self.qualificationPlaces.value(),
                                     self.qualificationBestOf.value())

    def loadQualificationSettings(self, competitionOptions):
        settings = QualificationSettings.fromOptions(competitionOptions)
        controls = (self.qualificationBox, self.qualificationPlaces,
                    self.qualificationBest, self.qualificationBestOf)
        # not a user edit: loading an event mustn't mark it as changed
        for w in controls:
            w.blockSignals(True)
        try:
            self.qualificationBox.setChecked(settings.mode != MODE_OFF)
            self.qualificationPlaces.setValue(settings.places)
            self.qualificationBest.setChecked(settings.mode == MODE_TOP_PLUS_BEST)
            self.qualificationBestOf.setValue(settings.bestOf)
        finally:
            for w in controls:
                w.blockSignals(False)
        self.updateQualificationControls()

    def qualificationChanged(self):
        self.updateQualificationControls()
        options = self.qualificationSettings().toOptions()
        # saved with the event's competition options, like the resume data
        self.e.replaceCompetitionOptions(options)
        self.resumeFileOptionsSet.emit(options)
        if self.c is not None:
            self.updateResults(self.matchday.currentIndex())

    def updateQualificationControls(self):
        multipleGroups = len(self.sl.groups) > 1
        for w in (self.qualificationPerGroup, self.qualificationBest,
                  self.qualificationBestOf, self.qualificationBestLabel):
            w.setVisible(multipleGroups)
        best = self.qualificationBest.isChecked()
        self.qualificationBestOf.setEnabled(best)
        self.qualificationBestLabel.setEnabled(best)
        self.qualificationBestLabel.setText("%s-placed" % ordinal(self.qualificationPlaces.value() + 1))
        self.qualificationPlaces.setToolTip(
            "Places that qualify from each group" if multipleGroups else "Places that qualify")
        self.qualificationBestOf.setToolTip(
            "How many %s-placed finishers qualify" % ordinal(self.qualificationPlaces.value() + 1))

    def clear(self):
        self.e = XkorEvent()
        self.rp = XkorRPList()
        self.s = XkorSport()
        self.sl = XkorStartList()
        self.textedit.setPlainText("")
        self.matchday.clear()
        self.matchday.hide()
        self.oddsAction.setEnabled(False)
        self.qualificationBox.hide()

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
        if self.c is None or self.c.matchdays() == 0:
            # nothing to score: without this the checks below offer to
            # regenerate matchday -1, naming a round that doesn't exist
            message_box(
                self, "There is nothing to scorinate yet.",
                QMessageBox.Ok,
                informativeText="This event doesn't have any rounds to generate. "
                                "Check the participants and groups you've set up.").exec()
            return

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

        # resume file
        resumeOpts = self.c.resumeFileOptions()
        self.lastMatchday = md

        # set resume file options
        self.resumeFileOptionsSet.emit(resumeOpts)
        self.resultConfirmed.emit(md, self.c.results(md))
        self.updateCompetition(resumeOpts, md, self.c.results(md))
        # shown from the rebuilt competition: only it has the saved matches
        # (or heat ranks) that the qualification markers are worked out from.
        # We show the selected matchday, not necessarily the one just scorinated
        self.updateResults(self.matchday.currentIndex())
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

        # before the matchday list is filled: filling it shows the results
        self.loadQualificationSettings(event.competitionOptions())
        self.qualificationBox.setVisible(self.c.supportsQualifications())

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
        # ask the competition, not the event: a bracket that has been
        # rearranged drops the results it no longer describes, and the event
        # still holds the stale text — the button stayed enabled over a view
        # that had gone blank
        shown = "" if self.c is None else self.c.results(self.matchday.currentIndex())
        self.exportResultsAction.setEnabled(bool(shown))

    def updateCompetition(self, resumeFileOptions, matchday, result):
        self.e.replaceCompetitionOptions(resumeFileOptions)
        self.e.setResult(matchday, result)

        from ..competitions.competitionfactory import XkorCompetitionFactory

        self.c = XkorCompetitionFactory.newCompetitionFull(
            self.e.competition(), self.sl, self.s, self.e.paradigmOptions(),
            self.e.competitionOptions(), self.e.results())

    def updateResults(self, matchday):
        text = self.c.results(matchday)
        try:
            text = self.c.formatQualifications(text, matchday, self.qualificationSettings())
        except Exception:
            # the markers are decoration: an event saved by an older version
            # (or edited by hand) that they can't make sense of still has to
            # show its results, so log the problem and show them plain
            traceback.print_exc(file=sys.stderr)
        self.textedit.setPlainText(self._formatResults(text))

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
