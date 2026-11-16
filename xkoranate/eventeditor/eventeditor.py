from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGridLayout, QLabel, QMessageBox, QPushButton,
                               QStackedLayout, QWidget)

from ..event import XkorEvent
from ..rplist import XkorRPList
from ..signuplist import XkorSignupList
from ..signuplisteditor.signuplisteditor import XkorSignupListEditor
from ..sport import XkorSport
from .. import theme
from ..ui.dialogs import confirm, text_preview_dialog
from .competitionselector import XkorCompetitionSelector
from .eventsetupwidget import XkorEventSetupWidget, pageNames
from .scorinatewidget import XkorScorinateWidget
from .sportselector import XkorSportSelector

_STEP_NAMES = ["Sport", "Signups", "Competition", "Groups", "Scorinate"]
_GROUPS_STEP = 3  # the step whose name depends on the competition type


class XkorEventEditor(QWidget):
    dataChanged = Signal()
    resultExportDirectoryChanged = Signal(str)
    signupListDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.stack = None
        self.signupListEditor = None
        self.eventSetupWidget = None  # built after the competition selector
        self.isLoading = False
        # the user chose to discard results by deleting a bracketed signup,
        # on this visit to the Signups page
        self._signupDiscardAnswered = False
        # the event exactly as loaded, while its sport isn't one we can select
        self._unresolvedEvent = None

        self.m_data = XkorEvent()
        self.m_rpList = XkorRPList()
        self.sport = XkorSport()

        self.initCompetitionSelector()
        self.initSportSelector()
        self.initSignupListEditor()
        self.initScorinateWidget()

        self.initEventSetupWidget()

        self.initLayout()

        # theme.MUTED differs between light/dark; the breadcrumb bakes it into
        # rich-text HTML, so it needs an explicit repaint on toggle
        theme.signal.changed.connect(self.updateStepIndicator)

    def goNext(self):
        if self.stack.currentIndex() == self.stack.count() - 2:  # we’re headed for the scorinate widget
            self.updateData()
            self.scorinateWidget.setEvent(self.m_data, self.m_rpList, self.sport)

        if self.stack.currentIndex() < self.stack.count() - 1:  # go to the next widget
            self.stack.setCurrentIndex(self.stack.currentIndex() + 1)
        self.updateNavigation()
        self.updateStepIndicator()

    def goPrev(self):
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self.updateNavigation()
        self.updateStepIndicator()

    def stepChanged(self, index):
        # a Discard lasts while the user stays on the page they gave it on
        if self.stack.widget(index) is not self.eventSetupWidget:
            self.eventSetupWidget.forgetResultsAnswer()
        if self.stack.widget(index) is not self.signupListEditor:
            self._signupDiscardAnswered = False

    def updateNavigation(self):
        """Go Back while there is a step behind; Continue while there is one
        ahead and a sport to take there.

        Worked out from the step and the sport every time, rather than nudged
        by whichever button was pressed: loading another event went back to
        the first step but left Go Back as it was, and Go Back then enabled
        Continue with no sport chosen, so the wizard could be walked all the
        way to Scorinate without one.
        """
        if self.stack is None:
            return  # still being built
        step = self.stack.currentIndex()
        self.prev.setEnabled(step > 0)
        self.next.setEnabled(step < self.stack.count() - 1 and self.sport.name() != "")

    def stepNames(self):
        names = list(_STEP_NAMES)
        names[_GROUPS_STEP] = pageNames(self.m_data.competition())[1]  # match the page's own heading
        return names

    def updateStepIndicator(self):
        # read-only reflection of the current stack page
        active = self.stack.currentIndex()
        parts = []
        for i, name in enumerate(self.stepNames()):
            if i == active:
                parts.append(
                    '<span style="color:%s; font-weight:600;">%d&nbsp;%s</span>'
                    % (theme.accent_text(), i + 1, name))
            else:
                parts.append(
                    '<span style="color:%s;">%d&nbsp;%s</span>'
                    % (theme.muted(), i + 1, name))
        sep = '<span style="color:%s;">&nbsp;&nbsp;›&nbsp;&nbsp;</span>' % theme.muted()
        self.stepIndicator.setText(sep.join(parts))

    def initCompetitionSelector(self):
        self.competitionSelector = XkorCompetitionSelector()
        self.competitionSelector.competitionChanged.connect(self.updateCompetition)
        self.competitionSelector.competitionOptionsChanged.connect(self.updateCompetitionOptions)

    def initEventSetupWidget(self):
        self.eventSetupWidget = XkorEventSetupWidget()
        self.eventSetupWidget.listChanged.connect(self.setDataChanged)
        self.eventSetupWidget.viewScheduleRequested.connect(self.viewSchedule)
        self.eventSetupWidget.resultsGuard = self.confirmDiscardBracketResults
        self.signupListEditor.itemDeleted.connect(self.eventSetupWidget.deleteAthlete)
        self.signupListEditor.deleteGuard = self.confirmDeletingBracketedSignups

    def initLayout(self):
        # stacked layout
        self.stack = QStackedLayout()
        self.stack.addWidget(self.sportSelector)
        self.stack.addWidget(self.signupListEditor)
        self.stack.addWidget(self.competitionSelector)
        self.stack.addWidget(self.eventSetupWidget)
        self.stack.addWidget(self.scorinateWidget)
        self.stack.setCurrentWidget(self.sportSelector)
        self.stack.currentChanged.connect(self.stepChanged)

        # step indicator (a read-only breadcrumb above the stack)
        self.stepIndicator = QLabel()
        self.stepIndicator.setTextFormat(Qt.RichText)
        self.stepIndicator.setAlignment(Qt.AlignCenter)
        self.stepIndicator.setContentsMargins(0, 4, 0, 8)

        # navigation bar
        self.prev = QPushButton("Go Back")
        self.prev.setDisabled(True)
        self.prev.clicked.connect(self.goPrev)
        self.next = QPushButton("Continue")
        self.next.setDisabled(True)
        self.next.setStyleSheet(theme.primary_button_qss())
        theme.signal.changed.connect(lambda: self.next.setStyleSheet(theme.primary_button_qss()))
        self.next.clicked.connect(self.goNext)

        # main layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.stepIndicator, 0, 0, 1, 3)
        self.layout.addLayout(self.stack, 1, 0, 1, 3)
        self.layout.addWidget(self.prev, 2, 1)
        self.layout.addWidget(self.next, 2, 2)
        self.layout.setColumnStretch(0, 1093)
        self.layout.setColumnStretch(1, 0)
        self.layout.setColumnStretch(2, 0)

        self.updateStepIndicator()

    def initScorinateWidget(self):
        self.scorinateWidget = XkorScorinateWidget()
        self.scorinateWidget.resumeFileOptionsSet.connect(self.setResumeFileOptions)
        self.scorinateWidget.resultConfirmed.connect(self.setResult)
        self.scorinateWidget.resultExportDirectoryChanged.connect(self.resultExportDirectoryChanged)

    def initSignupListEditor(self):
        self.signupListEditor = XkorSignupListEditor()
        self.signupListEditor.dataChanged.connect(self.updateSignupList)
        self.signupListEditor.signupListDirectoryChanged.connect(self.signupListDirectoryChanged)

    def initSportSelector(self):
        self.sportSelector = XkorSportSelector()
        self.sportSelector.sportChanged.connect(self.updateSport)
        self.sportSelector.paradigmOptionsChanged.connect(self.updateParadigmOptions)

    def loadSports(self):
        self.sportSelector.updateSportList()

    def data(self):
        if self._unresolvedEvent is not None:
            return self._unresolvedEvent.clone()
        self.updateData()
        return self.m_data.clone()  # XkorEvent is returned by value in the C++

    def setData(self, data, rpList):
        # XkorEvent and XkorRPList are passed by value in the C++
        data = data.clone()
        rpList = rpList.clone()
        loaded = data.clone()  # as stored, before the selectors below have their say
        self._unresolvedEvent = None

        self.isLoading = True  # prevent dataChanged from being emitted

        self.m_rpList = rpList

        # hit the reset button
        self.eventSetupWidget.reset()
        self.sportSelector.setSelectedSport("")
        self.signupListEditor.setData(XkorSignupList())
        self.competitionSelector.setSport(XkorSport(), {})
        self.eventSetupWidget.setGroups([])
        self.scorinateWidget.clear()
        self.stack.setCurrentIndex(0)
        self.updateNavigation()
        self.updateStepIndicator()

        self.m_data = data
        # data *is* m_data, and rebuilding the selectors below reports a
        # competition type back through updateCompetition, so hold on to the
        # one the file actually specified
        competition = data.competition()

        self.sportSelector.setParadigmOptions(data.paradigmOptions())
        self.sportSelector.setSelectedSport(data.sport())
        # updateSport is called implicitly by sportSelector->setSelectedSport
        self.competitionSelector.setSport(self.sport, data.competitionOptions())
        self.competitionSelector.setCompetition(competition)
        # the sport's paradigm may not offer the type the file asked for; the
        # selector's choice is what will actually be scorinated, so record
        # that rather than leaving the event claiming something the editor
        # isn't showing
        self.m_data.setCompetition(self.competitionSelector.competition())
        self.scorinateWidget.setEvent(self.m_data, self.m_rpList, self.sport)

        # signup lists
        self.signupListEditor.setData(data.signupList())

        # athletes
        self.eventSetupWidget.setSignupList(data.signupList())
        self.eventSetupWidget.setGroups(data.groups())

        if loaded.sport() and not self.sport.name():
            # The event names a sport that isn't installed: a custom file, or
            # one renamed since. Nothing can be selected for it, so the
            # selectors above fell back to "no sport" and wrote that, and
            # their default competition type, over the event. Just looking at
            # it was then enough for the next save to lose both. Hand back the
            # event as it was until the user picks a sport of their own.
            self._unresolvedEvent = loaded

        self.isLoading = False  # allow dataChanged to be emitted if the user does stuff

    def confirmDiscardBracketResults(self):
        """Ask before an edit throws away results already generated.

        A bracket only describes the tournament while the results match it,
        so rearranging one drops them. That is the right behaviour — showing
        results for a draw that no longer exists would be worse — but it used
        to happen with no warning at the point of the edit.
        """
        if not self.hasResults():
            return True
        return confirm(
            self, "Are you sure you want to change the bracket?",
            "This event has already been scorinated. Changing "
            "the bracket discards the results played from it.",
            accept=QMessageBox.Discard, destructive=True, acceptText="Discard Results")

    def hasResults(self):
        return any(self.m_data.results().values())

    def confirmDeletingBracketedSignups(self, ids):
        """Ask before deleting signups in a bracket that has been played.

        Their slots become byes, so the draw no longer matches the rounds
        played and the knockout stops showing them — the same loss a change
        on the bracket page asks about, but from a page that said nothing.
        A Discard lasts while the user stays on the Signups page.
        """
        if self._signupDiscardAnswered or not self.hasResults():
            return True
        setup = self.eventSetupWidget
        if not setup.isBracket() or not set(ids) & set(setup.realBracketEntrants()):
            return True
        accepted = confirm(
            self, "Are you sure you want to delete a participant in the bracket?",
            "This event has already been scorinated. Their place becomes a bye, "
            "which discards the results played from the bracket.",
            accept=QMessageBox.Discard, destructive=True, acceptText="Discard Results")
        if accepted:
            self._signupDiscardAnswered = True
        return accepted

    def setDataChanged(self):
        if not self.isLoading:
            self.dataChanged.emit()

    def setResult(self, matchday, result):
        self.m_data.setResult(matchday, result)
        self.setDataChanged()

    def setResumeFileOptions(self, options):
        self.m_data.replaceCompetitionOptions(options)
        self.setDataChanged()

    def updateCompetition(self, competition):
        self.m_data.setCompetition(competition)
        # the competition selector is built before these two, and emits while
        # it initialises, so both can still be absent here
        if self.eventSetupWidget is not None:
            self.eventSetupWidget.setCompetition(competition)
        if self.stack is not None:
            self.updateStepIndicator()
        self.setDataChanged()

    def updateCompetitionOptions(self, options):
        self.m_data.setCompetitionOptions(options)
        self.setDataChanged()

    def updateData(self):
        # bring the event up-to-date with whatever’s been going on in the GUI
        self.m_data.setSignupList(self.signupListEditor.data())
        self.m_data.setGroups(self.eventSetupWidget.groups())

    def updateParadigmOptions(self, options):
        # update the signup list editor
        self.signupListEditor.setSport(self.sport, options)
        self.m_data.setParadigmOptions(options)
        self.setDataChanged()

    def updateSignupList(self):
        self.m_data.setSignupList(self.signupListEditor.data())
        self.eventSetupWidget.setSignupList(self.signupListEditor.data())
        self.setDataChanged()

    def updateSport(self, s):
        resolved = None
        if not self.isLoading and s.name():
            # the user has chosen a sport for an event whose own wasn't found
            resolved, self._unresolvedEvent = self._unresolvedEvent, None
        self.sport = s.clone()  # XkorSport is passed by value in the C++
        self.m_data.setSport(self.sport.name(), self.sport.paradigm())
        self.updateNavigation()

        # update the signup list editor
        self.signupListEditor.setSport(self.sport, self.m_data.paradigmOptions())
        self.competitionSelector.setSport(self.sport, self.m_data.competitionOptions())
        if resolved is not None:
            self.restoreLoadedFormat(resolved)
        self.setDataChanged()

    def restoreLoadedFormat(self, loaded):
        """Put back the competition type and groups an event was loaded with.

        With no sport to go by, loading fell back to the selector's default
        type and laid the groups out for it, which drops a bracket's byes.
        Choosing a sport then kept that fallback: a knockout came back as a
        round robin, and its results were set aside as another type's. A
        sport that doesn't offer the loaded type keeps the selector's choice.
        """
        self.competitionSelector.setCompetition(loaded.competition())  # → updateCompetition
        self.eventSetupWidget.clear()
        self.eventSetupWidget.setGroups(loaded.groups())

    def viewSchedule(self):
        from ..competitions.competitionfactory import XkorCompetitionFactory

        self.updateData()
        startList = self.m_data.makeStartList(self.m_rpList)
        competition = XkorCompetitionFactory.newCompetitionFull(
            self.m_data.competition(), startList, self.sport,
            self.m_data.paradigmOptions(), self.m_data.competitionOptions(), {})

        schedule = competition.schedule()
        if schedule is None:
            schedule = "This competition type doesn't have a fixed schedule to preview."
        text_preview_dialog(self, "Full schedule", schedule)
