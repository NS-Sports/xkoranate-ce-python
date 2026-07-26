from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGridLayout, QLabel, QPushButton, QStackedLayout,
                               QWidget)

from ..event import XkorEvent
from ..group import XkorGroup
from ..rplist import XkorRPList
from ..signuplist import XkorSignupList
from ..signuplisteditor.signuplisteditor import XkorSignupListEditor
from ..sport import XkorSport
from .. import theme
from ..ui.dialogs import text_preview_dialog
from .competitionselector import XkorCompetitionSelector
from .eventsetupwidget import XkorEventSetupWidget
from .scorinatewidget import (XkorScorinateWidget, _cloneEvent, _cloneRPList,
                              _cloneSport)
from .sportselector import XkorSportSelector

_STEP_NAMES = ["Sport", "Signups", "Competition", "Groups", "Scorinate"]
_PLANNER_STEP = 3  # the step a competition may replace with a planner of its own
_EVERYONE = "Entries"  # the group a groupless competition fields


class XkorEventEditor(QWidget):
    dataChanged = Signal()
    resultExportDirectoryChanged = Signal(str)
    signupListDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.selectionModel = None
        self.stack = None
        self.stepNames = list(_STEP_NAMES)
        self.usesGroups = True
        self.signupListEditor = None
        self.isLoading = False

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
        self.prev.setDisabled(False)
        if self.stack.currentIndex() == self.stack.count() - 2:  # we’re headed for the scorinate widget
            self.updateData()
            self.scorinateWidget.setEvent(self.m_data, self.m_rpList, self.sport)
            self.next.setDisabled(True)

        if self.stack.currentIndex() < self.stack.count() - 1:  # go to the next widget
            self.stack.setCurrentIndex(self.stack.currentIndex() + 1)
        self.updateStepIndicator()

    def goPrev(self):
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex() - 1)

        self.next.setDisabled(False)
        if self.stack.currentIndex() == 0:
            self.prev.setDisabled(True)
        self.updateStepIndicator()

    def updateStepIndicator(self):
        # read-only reflection of the current stack page
        active = self.stack.currentIndex()
        parts = []
        for i, name in enumerate(self.stepNames):
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
        self.signupListEditor.itemDeleted.connect(self.eventSetupWidget.deleteAthlete)

        # step 4 is the groups editor for most competitions, but one that fields
        # everybody can put something more useful there — a season calendar, say
        self.plannerWidget = None
        self.plannerHost = QWidget()
        self.plannerStack = QStackedLayout(self.plannerHost)
        self.plannerStack.setContentsMargins(0, 0, 0, 0)
        self.plannerStack.addWidget(self.eventSetupWidget)

    def updatePlanner(self, competition):
        """Swap step 4 between the group editor and the competition's own
        planner, and rename it in the breadcrumb to match."""
        from ..competitions.competitionfactory import XkorCompetitionFactory

        try:
            c = XkorCompetitionFactory.newCompetition(competition)
        except ImportError:
            return

        if self.plannerWidget:
            self.plannerStack.removeWidget(self.plannerWidget)
            self.plannerWidget.setParent(None)
            self.plannerWidget.deleteLater()
            self.plannerWidget = None

        self.plannerWidget = c.newPlannerWidget(self.m_data.competitionOptions())
        if self.plannerWidget is not None:
            self.plannerStack.addWidget(self.plannerWidget)
            self.plannerStack.setCurrentWidget(self.plannerWidget)
            self.plannerWidget.optionsChanged.connect(self.updateCompetitionOptions)
        else:
            self.plannerStack.setCurrentWidget(self.eventSetupWidget)

        self.stepNames[_PLANNER_STEP] = c.plannerStepName()
        self.usesGroups = c.usesGroups()
        self.updateStepIndicator()

    def fieldEveryone(self):
        """The single group a groupless competition races: everyone signed up.
        Without it makeStartList() would hand the paradigm an empty field."""
        signupList = self.signupListEditor.data()
        return [XkorGroup(_EVERYONE, [a.id for a in signupList.athletes()])]

    def initLayout(self):
        # stacked layout
        self.stack = QStackedLayout()
        self.stack.addWidget(self.sportSelector)
        self.stack.addWidget(self.signupListEditor)
        self.stack.addWidget(self.competitionSelector)
        self.stack.addWidget(self.plannerHost)
        self.stack.addWidget(self.scorinateWidget)
        self.stack.setCurrentWidget(self.sportSelector)

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
        self.scorinateWidget.resultExportDirectoryChanged.connect(self.setResultExportDirectory)

    def initSignupListEditor(self):
        self.signupListEditor = XkorSignupListEditor()
        self.signupListEditor.dataChanged.connect(self.updateSignupList)
        self.signupListEditor.signupListDirectoryChanged.connect(self.setSignupListDirectory)

    def initSportSelector(self):
        self.sportSelector = XkorSportSelector()
        self.sportSelector.sportChanged.connect(self.updateSport)
        self.sportSelector.paradigmOptionsChanged.connect(self.updateParadigmOptions)

    def loadSports(self):
        self.sportSelector.updateSportList()

    def data(self):
        self.updateData()
        return _cloneEvent(self.m_data)  # XkorEvent is returned by value in the C++

    def setData(self, data, rpList):
        # XkorEvent and XkorRPList are passed by value in the C++
        data = _cloneEvent(data)
        rpList = _cloneRPList(rpList)

        self.isLoading = True  # prevent dataChanged from being emitted

        self.m_rpList = rpList

        # hit the reset button
        self.eventSetupWidget.clear()
        self.sportSelector.setSelectedSport("")
        self.signupListEditor.setData(XkorSignupList())
        self.competitionSelector.setSport(XkorSport(), {})
        self.eventSetupWidget.setGroups([])
        self.scorinateWidget.clear()
        self.stack.setCurrentIndex(0)
        self.updateStepIndicator()

        self.m_data = data

        self.sportSelector.setParadigmOptions(data.paradigmOptions())
        self.sportSelector.setSelectedSport(data.sport())
        # updateSport is called implicitly by sportSelector->setSelectedSport
        self.competitionSelector.setSport(self.sport, data.competitionOptions())
        self.competitionSelector.setCompetition(data.competition())
        self.scorinateWidget.setEvent(self.m_data, self.m_rpList, self.sport)

        # signup lists
        self.signupListEditor.setData(data.signupList())

        # athletes
        self.eventSetupWidget.setSignupList(data.signupList())
        self.eventSetupWidget.setGroups(data.groups())

        self.isLoading = False  # allow dataChanged to be emitted if the user does stuff

    def setDataChanged(self):
        if not self.isLoading:
            self.dataChanged.emit()

    def setResult(self, matchday, result):
        self.m_data.setResult(matchday, result)
        self.setDataChanged()

    def setResultExportDirectory(self, dir):
        self.resultExportDirectoryChanged.emit(dir)

    def setResumeFileOptions(self, options):
        self.m_data.replaceCompetitionOptions(options)
        self.setDataChanged()

    def setSignupListDirectory(self, dir):
        self.signupListDirectoryChanged.emit(dir)

    def updateCompetition(self, competition):
        self.m_data.setCompetition(competition)
        self.updatePlanner(competition)
        if not self.usesGroups:
            self.m_data.setGroups(self.fieldEveryone())
        self.setDataChanged()

    def updateCompetitionOptions(self, options):
        self.m_data.setCompetitionOptions(options)
        self.setDataChanged()

    def updateData(self):
        # bring the event up-to-date with whatever’s been going on in the GUI
        self.m_data.setSignupList(self.signupListEditor.data())
        if self.usesGroups:
            self.m_data.setGroups(self.eventSetupWidget.groups())
        else:
            self.m_data.setGroups(self.fieldEveryone())

    def updateParadigmOptions(self, options):
        # update the signup list editor
        self.signupListEditor.setSport(self.sport, options)
        self.m_data.setParadigmOptions(options)
        self.setDataChanged()

    def updateSignupList(self):
        self.m_data.setSignupList(self.signupListEditor.data())
        self.eventSetupWidget.setSignupList(self.signupListEditor.data())
        if not self.usesGroups:
            # a new signup joins the field straight away
            self.m_data.setGroups(self.fieldEveryone())
        self.setDataChanged()

    def updateSport(self, s):
        self.sport = _cloneSport(s)  # XkorSport is passed by value in the C++
        self.m_data.setSport(self.sport.name(), self.sport.paradigm())
        if self.sport.name() != "":
            self.next.setEnabled(True)
        else:
            self.next.setEnabled(False)

        # update the signup list editor
        self.signupListEditor.setSport(self.sport, self.m_data.paradigmOptions())
        self.competitionSelector.setSport(self.sport, self.m_data.competitionOptions())
        self.setDataChanged()

    def updateSportList(self):
        self.sportSelector.updateSportList()

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
