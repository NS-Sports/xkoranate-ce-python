import uuid

from PySide6.QtCore import QItemSelectionModel, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractItemView, QGridLayout, QLabel, QStackedLayout,
                               QStyle, QToolBar, QTreeWidgetItem, QTreeWidgetItemIterator,
                               QWidget)

from ..abstracttreewidget import XkorAbstractTreeWidget
from ..ui.typography import heading_label
from .. import theme
from ..athlete import BYE_ID, BYE_NAME, XkorAthlete
from ..exceptions import XkorSearchFailedException
from ..competitions import bracket
from ..group import XkorGroup
from ..icons import icon_action
from ..rng import Mt19937
from ..signuplist import XkorSignupList
from .eventsetupdelegate import XkorEventSetupDelegate


def _uuidToString(u):
    if u is None:  # null QUuid
        return "{00000000-0000-0000-0000-000000000000}"
    return "{%s}" % u


def _uuidFromString(s):
    try:
        u = uuid.UUID(str(s).strip("{}"))
    except (AttributeError, TypeError, ValueError):
        return None
    return None if u.int == 0 else u


def _cloneSignupList(sl):
    rval = XkorSignupList()
    rval.ath = [a.clone() for a in sl.ath]
    rval.min = sl.min
    rval.max = sl.max
    return rval


class XkorEventSetupWidget(XkorAbstractTreeWidget):
    slChanged = Signal()
    viewScheduleRequested = Signal()

    def __init__(self):
        super().__init__()
        self.availableAthleteNames = []  # mutated in place: shared with the delegate
        self.availableAthletes = []  # list of QUuid; shared with the delegate
        self.sl = XkorSignupList()
        self.r = Mt19937()  # backs std::random_shuffle in randomizeGroup
        self.competition = ""  # retitles the page; set by the event editor
        self.bracketGroupName = "Bracket"  # the pooled group a knockout stores
        self.headingLabel = None  # created in setupLayout(), below

        self._delegate = XkorEventSetupDelegate(self.availableAthleteNames, self.availableAthletes)
        self.treeWidget.setItemDelegate(self._delegate)
        self.treeWidget.setColumnCount(1)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setDragDropMode(QAbstractItemView.InternalMove)
        rootItem = self.treeWidget.invisibleRootItem()
        rootItem.setFlags(rootItem.flags() & ~Qt.ItemIsDropEnabled)

        # set up actions
        self.insertGroupAction = icon_action("add", "Create a group", self)
        self.insertGroupAction.triggered.connect(self.insertItem)

        self.insertAthleteAction = icon_action("add-participant", "Add a participant", self)
        self.insertAthleteAction.setEnabled(False)
        self.insertAthleteAction.triggered.connect(self.insertAthlete)

        self.insertAllAction = icon_action("add-all-participants", "Add all available participants", self)
        self.insertAllAction.setEnabled(False)
        self.insertAllAction.triggered.connect(self.insertAll)

        self.randomizeAction = icon_action("roll", "Randomize this group", self)
        self.randomizeAction.setEnabled(False)
        self.randomizeAction.triggered.connect(self.randomizeGroup)

        self.seedAction = icon_action("seed", "Seed the draw by skill", self)
        self.seedAction.setToolTip(
            "Arrange the bracket so the strongest entrant faces the weakest, "
            "and the top two can only meet in the final.")
        self.seedAction.triggered.connect(self.seedBracket)

        self.spreadSeedsAction = icon_action("spread-seeds", "Keep the top seeds apart", self)
        self.spreadSeedsAction.setToolTip(
            "Spread the strongest entrants evenly across the bracket so they "
            "can't meet early, and draw everyone else at random around them.")
        self.spreadSeedsAction.triggered.connect(self.spreadSeeds)

        self.scheduleAction = icon_action("schedule", "View full schedule", self)
        self.scheduleAction.triggered.connect(lambda: self.viewScheduleRequested.emit())

        actions = [self.insertGroupAction, self.insertAthleteAction,
                   self.insertAllAction, self.deleteAction, self.randomizeAction,
                   self.seedAction, self.spreadSeedsAction,
                   None, self.scheduleAction]
        self.setupLayout(actions)

        self.slChanged.connect(self.updateAvailableAthletes)

        # a drag can leave a match holding one or three entrants, so re-pair
        # the bracket once the drop has settled
        self.treeWidget.model().rowsInserted.connect(self.scheduleReflow)
        self.treeWidget.model().rowsRemoved.connect(self.scheduleReflow)
        # picking a bye for a slot doesn't add or remove rows, so relabel on
        # a plain data change too
        self.treeWidget.model().dataChanged.connect(self.updateMatchLabels)
        self.updateBracketActions()

    def insertionText(self):
        return "Create a group"

    def isBracket(self):
        return self.competition == "singleElimination"

    def matchLabel(self, index):
        return "Match %d" % (index + 1)

    def renumberMatches(self):
        """Keep the match labels in step with their positions and contents."""
        for i in range(self.treeWidget.topLevelItemCount()):
            match = self.treeWidget.topLevelItem(i)
            ids = [_uuidFromString(match.child(j).data(0, Qt.UserRole))
                   for j in range(match.childCount())]
            # a match of nothing but byes has nobody to send to the next round
            empty = bool(ids) and all(id is None or id == BYE_ID for id in ids)
            match.setText(0, self.matchLabel(i) + ("  (nobody in this match)" if empty else ""))

    def updateMatchLabels(self, *args):
        if self.isInUse or not self.isBracket():
            return
        self.renumberMatches()

    def bracketEntrants(self):
        """Every entrant id in the bracket, in slot order (byes included)."""
        rval = []
        for i in range(self.treeWidget.topLevelItemCount()):
            match = self.treeWidget.topLevelItem(i)
            for j in range(match.childCount()):
                rval.append(_uuidFromString(match.child(j).data(0, Qt.UserRole)))
        return rval

    def setBracketSlots(self, slots):
        """Rebuild the tree from a slot list, two slots to a match."""
        self.isInUse = True
        self.treeWidget.clear()
        for m in range(len(slots) // 2):
            match = self.createItem()
            match.setExpanded(True)
            self.initItem(match, self.matchLabel(m))
            for slot in (slots[2 * m], slots[2 * m + 1]):
                self.initAthlete(self.createAthlete(match), slot)
        self.isInUse = False
        self.listChanged.emit()

    def headingText(self):
        # a knockout is one pooled bracket rather than a set of groups, so
        # the page is named for what the user is actually arranging
        if self.competition == "singleElimination":
            return "Set bracket"
        return "Set up groups"

    def setCompetition(self, competition):
        if competition == self.competition:
            return
        previous = self.groups()  # read the tree in its old shape
        self.competition = competition
        if self.headingLabel is not None:
            self.headingLabel.setText(self.headingText())
        self.updateBracketActions()
        if previous:
            # re-render: groups become matches, or matches pool back together
            self.clear()
            self.setGroups(previous)
        self.updateButtons()

    def updateBracketActions(self):
        isBracket = self.isBracket()
        # matches aren't user-created — the draw makes them
        self.insertGroupAction.setVisible(not isBracket)
        self.insertAthleteAction.setVisible(not isBracket)
        self.seedAction.setVisible(isBracket)
        self.spreadSeedsAction.setVisible(isBracket)
        self.randomizeAction.setToolTip(
            "Draw the bracket at random." if isBracket else "Randomize this group.")
        # a bye is only meaningful inside a bracket
        self._delegate.allowBye = isBracket

    def scheduleReflow(self, *args):
        if self.isInUse or not self.isBracket():
            return
        QTimer.singleShot(0, self.reflowBracket)

    def reflowBracket(self):
        """Re-pair the bracket after a drag, keeping the visual order."""
        if self.isInUse or not self.isBracket():
            return
        slots = self.padToBracket(self.bracketEntrants())
        if slots != self.bracketEntrants():
            self.setBracketSlots(slots)
        else:
            self.renumberMatches()

    def createAthlete(self, parent):
        item = QTreeWidgetItem(parent)
        self.treeWidget.setCurrentItem(item, 0)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        return item

    def deleteAthlete(self, id):
        toDelete = []
        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            item = i.value()
            # if this is an athlete, look up its ID
            if item.parent():
                if _uuidFromString(item.data(0, Qt.UserRole)) == id:
                    toDelete.append(item)
            i += 1
        for item in toDelete:
            parent = item.parent()
            parent.takeChild(parent.indexOfChild(item))
        self.listChanged.emit()

    def getAthleteByID(self, id):
        rval = XkorAthlete()
        try:
            rval = self.sl.getAthleteByID(id)
        except XkorSearchFailedException:
            pass

        if rval == XkorAthlete():
            err = "No athlete with ID "
            err += _uuidToString(id)
            err += " in XkorEventEditor::getAthleteBySN(QString)"
            raise XkorSearchFailedException(err)
        return rval

    def groups(self):
        if self.isBracket():
            # the tree holds matches, but the event still stores one pooled
            # group — slot order is what the bracket is read from
            return [XkorGroup(self.bracketGroupName, self.bracketEntrants())]

        rval = []
        for i in range(self.treeWidget.topLevelItemCount()):
            group = XkorGroup()
            group.name = self.treeWidget.topLevelItem(i).text(0)
            for j in range(self.treeWidget.topLevelItem(i).childCount()):
                group.athletes.append(_uuidFromString(self.treeWidget.topLevelItem(i).child(j).data(0, Qt.UserRole)))
            rval.append(group)
        return rval

    def initAthlete(self, athlete, id=None):
        if id == BYE_ID:
            athlete.setText(0, "— %s —" % BYE_NAME)
        else:
            # get the actual athlete so we can display its name
            try:
                a = self.getAthleteByID(id)
                athlete.setText(0, a.name + " (" + a.nation + ")")
            except XkorSearchFailedException:
                athlete.setText(0, "<unknown participant>")

        athlete.setFlags(athlete.flags() & ~Qt.ItemIsDropEnabled)
        athlete.setData(0, Qt.UserRole, _uuidToString(id))

    def initItem(self, group, groupName=""):  # initItem is used for groups
        group.setFlags((group.flags() | Qt.ItemIsDropEnabled) & ~Qt.ItemIsDragEnabled)
        group.setText(0, groupName)

    def insertAll(self):
        if self.isBracket():
            slots = [i for i in self.bracketEntrants() if i not in (None, BYE_ID)]
            slots.extend(self.availableAthletes)
            self.setBracketSlots(self.padToBracket(slots))
            return

        self.isInUse = True
        selection = self.treeWidget.selectedItems()
        parent = selection[0].parent()

        for i in range(len(self.availableAthletes)):
            self.initAthlete(self.createAthlete(parent if parent else selection[0]),
                             self.availableAthletes[i])
        self.isInUse = False
        self.listChanged.emit()

    def insertAthlete(self):
        self.isInUse = True
        selection = self.treeWidget.selectedItems()

        self.treeWidget.setCurrentItem(selection[0], 0, QItemSelectionModel.Clear)
        parent = selection[0].parent()

        athlete = self.createAthlete(parent if parent else selection[0])
        self.initAthlete(athlete)
        self.treeWidget.editItem(athlete, 0)
        self.isInUse = False
        self.listChanged.emit()

    def redrawBracket(self, drawFunction):
        """Rebuild the bracket with one of the draw functions in bracket.py."""
        athletes = []
        for id in self.bracketEntrants():
            if id is None or id == BYE_ID:
                continue
            try:
                athletes.append(self.getAthleteByID(id))
            except XkorSearchFailedException:
                pass
        if len(athletes) < 2:
            return
        slots = drawFunction(athletes, bracket.bracketSize(len(athletes)))
        self.setBracketSlots([BYE_ID if a is None else a.id for a in slots])

    def seedBracket(self):
        self.redrawBracket(bracket.drawSeeded)

    def spreadSeeds(self):
        from PySide6.QtWidgets import QInputDialog

        entrants = len([i for i in self.bracketEntrants() if i not in (None, BYE_ID)])
        if entrants < 2:
            return
        count, ok = QInputDialog.getInt(
            self, "Keep the top seeds apart", "How many seeds?",
            min(4, entrants), 2, entrants)
        if not ok:
            return
        self.redrawBracket(
            lambda a, size: bracket.drawVariableSeeds(a, size, count, self.r))

    def padToBracket(self, slots):
        """Round a slot list up to a usable bracket, adding byes as needed."""
        real = [i for i in slots if i is not None and i != BYE_ID]
        if len(real) < 2:
            return []
        size = bracket.bracketSize(len(real))

        laid = [None if (i is None or i == BYE_ID) else i for i in slots][:size]
        if not bracket.isWellFormed(laid, real):
            laid = bracket.drawManual(real, size)
        return [BYE_ID if i is None else i for i in laid]

    def randomizeGroup(self):
        if self.isBracket():
            # the dice is the random draw: there is no separate seeding mode
            self.redrawBracket(lambda a, size: bracket.drawRandom(a, size, self.r))
            return

        self.isInUse = True
        selection = self.treeWidget.selectedItems()

        # iterate in reverse so that the first group will be selected when we’re done
        for group in reversed(selection):
            if group.parent():
                group = group.parent()

            groupMembers = group.takeChildren()
            self.r.shuffle(groupMembers)  # std::random_shuffle
            group.addChildren(groupMembers)
            for j in groupMembers:
                self.treeWidget.setCurrentItem(j, 0, QItemSelectionModel.Select)
            self.treeWidget.setCurrentItem(group, 0, QItemSelectionModel.Select)
        self.isInUse = False
        self.listChanged.emit()

    def setGroups(self, g):
        if self.isBracket():
            if g:
                self.bracketGroupName = g[0].name
            slots = []
            for i in g:
                slots.extend(i.athletes)
            self.setBracketSlots(self.padToBracket(slots))
            return

        self.isInUse = True
        for i in g:
            group = self.createItem()
            group.setExpanded(True)
            self.initItem(group, i.name)
            for j in i.athletes:
                if j == BYE_ID:
                    continue  # a bye only means anything inside a bracket
                athlete = self.createAthlete(group)
                self.initAthlete(athlete, j)
        self.isInUse = False
        self.listChanged.emit()

    def setSignupList(self, l):
        self.sl = _cloneSignupList(l)
        self.slChanged.emit()

    def setupLayout(self, actions):
        # label
        self.headingLabel = heading_label(self.headingText(), level=1, center=True)

        # tool bar
        toolBar = QToolBar()
        small = self.style().pixelMetric(QStyle.PM_SmallIconSize)
        toolBar.setIconSize(QSize(small, small))
        for i in actions:
            if i is None:
                toolBar.addSeparator()
            else:
                toolBar.addAction(i)

        # empty-state hint, layered over the tree so a first-time user isn't
        # left staring at a blank rectangle
        self._emptyLabel = QLabel(self.emptyStateText())
        self._emptyLabel.setAlignment(Qt.AlignCenter)
        self._emptyLabel.setWordWrap(True)
        self._emptyLabel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._restyleEmptyLabel()
        theme.signal.changed.connect(self._restyleEmptyLabel)

        treeArea = QWidget()
        treeStack = QStackedLayout(treeArea)
        treeStack.setStackingMode(QStackedLayout.StackAll)
        treeStack.addWidget(self.treeWidget)
        treeStack.addWidget(self._emptyLabel)

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.headingLabel, 0, 0, Qt.AlignCenter)
        self.layout.addWidget(treeArea, 1, 0)
        self.layout.addWidget(toolBar, 2, 0, Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.updateEmptyState()

    def updateButtons(self):
        selection = self.treeWidget.selectedItems()

        if self.isBracket():
            entrants = len([i for i in self.bracketEntrants() if i not in (None, BYE_ID)])
            # a draw acts on the whole bracket, so it needs no selection
            self.deleteAction.setEnabled(len(selection) > 0)
            self.insertAllAction.setEnabled(len(self.availableAthletes) > 0)
            for action in (self.randomizeAction, self.seedAction, self.spreadSeedsAction):
                action.setEnabled(entrants >= 2)
            return

        self.deleteAction.setEnabled(len(selection) > 0)
        self.insertAthleteAction.setEnabled(len(self.availableAthletes) > 0)
        self.insertAllAction.setEnabled(len(self.availableAthletes) > 0)
        self.randomizeAction.setEnabled(len(selection) > 0)

        if len(selection) != 1:
            # can’t manipulate athletes if more than one is selected
            self.insertAthleteAction.setEnabled(False)
            self.insertAllAction.setEnabled(False)

    def updateAvailableAthletes(self):
        self.availableAthletes.clear()
        self.availableAthleteNames.clear()

        s = self.sl.athletes()
        for j in s:
            self.availableAthletes.append(j.id)
            self.availableAthleteNames.append(j.name + " (" + j.nation + ")")

        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            item = i.value()
            # if this is an athlete, look up its ID
            if item.parent():
                try:
                    temp = self.getAthleteByID(_uuidFromString(item.data(0, Qt.UserRole)))
                    item.setText(0, temp.name + " (" + temp.nation + ")")
                except XkorSearchFailedException:
                    item.setText(0, "<unknown participant>")
            i += 1
        self.listChanged.emit()
