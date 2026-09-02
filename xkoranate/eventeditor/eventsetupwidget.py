
from PySide6.QtCore import QItemSelectionModel, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QGridLayout, QHBoxLayout,
                               QLabel, QStackedLayout, QStyle, QToolBar, QTreeWidgetItem,
                               QTreeWidgetItemIterator, QWidget)

from ..uuids import parseAssignedUuid, uuidToString
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
        self.bracketSlotCount = 0  # how many slots the user has asked for
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

        self.bracketSizeCombo = QComboBox()
        for size in self.BRACKET_SIZES:
            self.bracketSizeCombo.addItem("%d-participant bracket" % size, size)
        self.bracketSizeCombo.setToolTip(
            "How many slots the bracket has. Any slot you don't fill is a bye.")
        self.bracketSizeCombo.currentIndexChanged.connect(self.bracketSizeChosen)

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

    BRACKET_SIZES = [2, 4, 8, 16, 32, 64, 128]

    def isBracket(self):
        return self.competition == "singleElimination"

    def bracketSize(self):
        """How many slots the bracket has, from the dropdown."""
        if self.bracketSlotCount:
            return self.bracketSlotCount
        return len(self.bracketEntrants())

    def setBracketSize(self, size):
        """Resize the bracket, keeping the entrants that still fit.

        Growing it adds byes; shrinking it drops the entrants that fall off
        the end, which go back to the pool of available participants.
        """
        size = max(2, size)
        self.bracketSlotCount = size
        slots = self.realBracketEntrants()[:size]
        self.setBracketSlots(self.padToBracket(slots))
        self.syncBracketSizeCombo()

    def usableBracketSizes(self):
        """Sizes that can actually be played, given who is in the bracket.

        Every match needs at least one participant, so a bracket can hold at
        most twice as many slots as it has entrants — a 32-slot draw for four
        clubs would leave twelve matches with nobody in them, and the
        competition would quietly play a four-slot bracket instead.

        Smaller brackets are offered too: a 16-club signup list can still be
        run as an eight-club cup, and the clubs that don't fit go back to the
        pool of available participants.
        """
        entrants = len(self.realBracketEntrants())
        if entrants < 2:
            return list(self.BRACKET_SIZES)
        return [s for s in self.BRACKET_SIZES if s // 2 <= entrants]

    def syncBracketSizeCombo(self):
        """Show the size the bracket has, and the sizes it could usefully be."""
        size = self.bracketSize()
        sizes = self.usableBracketSizes()
        if size and size not in sizes:
            # a bracket loaded from a file may be a size we wouldn't offer
            sizes = sorted(set(sizes + [size]))

        self.bracketSizeCombo.blockSignals(True)
        self.bracketSizeCombo.clear()
        for s in sizes:
            self.bracketSizeCombo.addItem("%d-participant bracket" % s, s)
        index = self.bracketSizeCombo.findData(size)
        self.bracketSizeCombo.setCurrentIndex(max(0, index))
        self.bracketSizeCombo.blockSignals(False)

    def bracketSizeChosen(self, index):
        size = self.bracketSizeCombo.itemData(index)
        if size:
            self.setBracketSize(int(size))

    def matchLabel(self, index):
        return "Match %d" % (index + 1)

    def renumberMatches(self):
        """Keep the match labels in step with their positions and contents."""
        for i in range(self.treeWidget.topLevelItemCount()):
            match = self.treeWidget.topLevelItem(i)
            ids = [parseAssignedUuid(match.child(j).data(0, Qt.UserRole))
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
                rval.append(parseAssignedUuid(match.child(j).data(0, Qt.UserRole)))
        return rval

    def realBracketEntrants(self):
        """Bracket slots holding an actual participant, byes excluded."""
        return [i for i in self.bracketEntrants() if i is not None and i != BYE_ID]

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
        self.bracketSizeCombo.setVisible(isBracket)

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
                if parseAssignedUuid(item.data(0, Qt.UserRole)) == id:
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
            err += uuidToString(id)
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
                group.athletes.append(parseAssignedUuid(self.treeWidget.topLevelItem(i).child(j).data(0, Qt.UserRole)))
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
        athlete.setData(0, Qt.UserRole, uuidToString(id))

    def initItem(self, group, groupName=""):  # initItem is used for groups
        group.setFlags((group.flags() | Qt.ItemIsDropEnabled) & ~Qt.ItemIsDragEnabled)
        group.setText(0, groupName)

    def insertAll(self):
        if self.isBracket():
            # fill the empty slots first, keeping the draw as it stands
            slots = list(self.bracketEntrants())
            pool = list(self.availableAthletes)
            for i in range(len(slots)):
                if not pool:
                    break
                if slots[i] is None or slots[i] == BYE_ID:
                    slots[i] = pool.pop(0)

            if pool or not slots:
                # more participants than slots: grow the bracket to hold them
                # all rather than leaving anyone out of a button called "add
                # all". Sizing to fit spreads the byes one to a match.
                everyone = [i for i in slots if i not in (None, BYE_ID)] + pool
                self.bracketSlotCount = 0
                laid = self.padToBracket(everyone)
                self.bracketSlotCount = len(laid)
            else:
                laid = self.padToBracket(slots)

            self.setBracketSlots(laid)
            self.syncBracketSizeCombo()
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

    def deleteItems(self):
        if self.isBracket():
            # emptying a slot leaves a bye behind: removing the row itself
            # would leave the bracket a size that isn't a power of two
            self.isInUse = True
            cleared = False
            for item in self.treeWidget.selectedItems():
                if item.parent() is None:
                    continue  # a match is structural, not deletable
                self.initAthlete(item, BYE_ID)
                cleared = True
            self.isInUse = False
            if cleared:
                self.renumberMatches()
                self.listChanged.emit()
            return
        super().deleteItems()

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
        size = max(self.bracketSlotCount, bracket.bracketSize(len(athletes)))
        slots = drawFunction(athletes, size)
        self.bracketSlotCount = size
        self.setBracketSlots([BYE_ID if a is None else a.id for a in slots])
        self.syncBracketSizeCombo()

    def seedBracket(self):
        self.redrawBracket(bracket.drawSeeded)

    def spreadSeeds(self):
        from PySide6.QtWidgets import QInputDialog

        entrants = len(self.realBracketEntrants())
        if entrants < 2:
            return
        count, ok = QInputDialog.getInt(
            self, "Keep the top seeds apart", "How many seeds?",
            min(4, entrants), 2, entrants)
        if not ok:
            return
        self.redrawBracket(
            lambda a, size: bracket.drawVariableSeeds(a, size, count, self.r))

    def padToBracket(self, slots, size=None):
        """Lay a slot list out over the bracket, padding short with byes.

        A participant can never appear twice, however the caller got there.
        With no size chosen the bracket is sized to fit and the byes are
        spread one to a match; once the user has picked a size, slots are
        laid out exactly as given so their arrangement is preserved.
        """
        laid = []
        placed = []
        for id in slots:
            if id is None or id == BYE_ID:
                laid.append(BYE_ID)
            elif id in placed:
                continue  # already in the bracket; don't add it again
            else:
                placed.append(id)
                laid.append(id)

        chosen = self.bracketSlotCount if size is None else size
        if not chosen:
            if len(placed) < 2:
                return []
            # nothing chosen yet: size to fit and spread the byes out
            chosen = bracket.bracketSize(len(placed))
            return [BYE_ID if i is None else i for i in bracket.drawManual(placed, chosen)]

        laid = laid[:chosen]
        while len(laid) < chosen:
            laid.append(BYE_ID)
        return laid

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
            # a saved bracket is already a full slot list, byes included, so
            # keep it exactly; a bare list of entrants gets sized to fit with
            # the byes spread one to a match
            isFullBracket = len(slots) >= 2 and not len(slots) & (len(slots) - 1)
            if isFullBracket:
                self.bracketSlotCount = len(slots)
                laid = self.padToBracket(slots, size=len(slots))
            else:
                self.bracketSlotCount = 0
                laid = self.padToBracket(slots)
                self.bracketSlotCount = len(laid)
            self.setBracketSlots(laid)
            self.syncBracketSizeCombo()
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

        # the bracket-size chooser sits with the tool bar, but is only
        # meaningful for a knockout
        controls = QWidget()
        controlsLayout = QHBoxLayout(controls)
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.addWidget(toolBar)
        controlsLayout.addWidget(self.bracketSizeCombo)

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.headingLabel, 0, 0, Qt.AlignCenter)
        self.layout.addWidget(treeArea, 1, 0)
        self.layout.addWidget(controls, 2, 0, Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.updateEmptyState()

    def updateButtons(self):
        # placements change as the user works, so what's still available has
        # to be recomputed rather than cached from when the list was loaded
        self.recomputeAvailableAthletes()
        selection = self.treeWidget.selectedItems()

        if self.isBracket():
            slots = [i for i in selection if i.parent() is not None]
            # matches are structural: the size dropdown decides how many
            # there are, so only the slots inside them can be cleared
            self.deleteAction.setEnabled(len(slots) > 0)
            self.insertAllAction.setEnabled(len(self.availableAthletes) > 0)
            entrants = len(self.realBracketEntrants())
            for action in (self.randomizeAction, self.seedAction, self.spreadSeedsAction):
                action.setEnabled(entrants >= 2)
            self.syncBracketSizeCombo()
            return

        self.deleteAction.setEnabled(len(selection) > 0)
        self.insertAthleteAction.setEnabled(len(self.availableAthletes) > 0)
        self.insertAllAction.setEnabled(len(self.availableAthletes) > 0)
        self.randomizeAction.setEnabled(len(selection) > 0)

        if len(selection) != 1:
            # can’t manipulate athletes if more than one is selected
            self.insertAthleteAction.setEnabled(False)
            self.insertAllAction.setEnabled(False)

    def placedAthletes(self):
        """Ids already sitting in the tree, so they aren't offered twice."""
        rval = []
        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            item = i.value()
            if item.parent():
                id = parseAssignedUuid(item.data(0, Qt.UserRole))
                if id is not None and id != BYE_ID:
                    rval.append(id)
            i += 1
        return rval

    def recomputeAvailableAthletes(self):
        """Participants not yet in the tree. Emits nothing, so it is safe to
        call from updateButtons (which listChanged already drives)."""
        self.availableAthletes.clear()
        self.availableAthleteNames.clear()
        placed = self.placedAthletes()
        for j in self.sl.athletes():
            if j.id in placed:
                continue
            self.availableAthletes.append(j.id)
            self.availableAthleteNames.append(j.name + " (" + j.nation + ")")

    def updateAvailableAthletes(self):
        self.recomputeAvailableAthletes()

        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            item = i.value()
            # if this is an athlete, look up its ID
            if item.parent():
                id = parseAssignedUuid(item.data(0, Qt.UserRole))
                if id == BYE_ID:
                    i += 1
                    continue  # a bye has no participant to look up
                try:
                    temp = self.getAthleteByID(id)
                    item.setText(0, temp.name + " (" + temp.nation + ")")
                except XkorSearchFailedException:
                    item.setText(0, "<unknown participant>")
            i += 1
        self.listChanged.emit()
