import time
import uuid

from PySide6.QtCore import QItemSelectionModel, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QAbstractItemView, QFrame, QTreeWidgetItem

from .uuids import parseAssignedUuid, uuidToString
from .abstracttreewidget import XkorAbstractTreeWidget
from .event import XkorEvent
from .icons import icon_action
from .rng import Mt19937
from .rplist import XkorRPList


class XkorNavigationWidget(XkorAbstractTreeWidget):
    editEvent = Signal(object)  # XkorEvent
    editRPList = Signal(object)  # XkorRPList

    def __init__(self):
        super().__init__()
        self.r = Mt19937()
        self.r.seed(int(time.time()))

        self.m_rpListItem = None
        self.m_eventsItem = None

        # store the actual data
        self.m_events = {}  # QUuid -> XkorEvent
        self.m_rpList = None

        # let the application theme own the sidebar background; just keep the
        # frameless look and drop the native focus rect
        self.treeWidget.setFrameStyle(QFrame.NoFrame)
        self.treeWidget.setAttribute(Qt.WA_MacShowFocusRect, False)

        self.treeWidget.setColumnCount(1)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setAlternatingRowColors(False)
        self.treeWidget.setDragDropMode(QAbstractItemView.InternalMove)
        self.treeWidget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.m_insertSheetAction = icon_action("add", "New event", self)
        self.m_insertSheetAction.setEnabled(True)
        self.m_insertSheetAction.triggered.connect(self.insertItem)

        self.deleteAction.setToolTip("Remove event")
        self.deleteAction.triggered.connect(self.correctSelectionAfterDelete)

        actions = [self.m_insertSheetAction, self.deleteAction]
        self.setupLayout(actions)

        self.createCategories()

        self.treeWidget.itemSelectionChanged.connect(self.editItem)

    def correctSelectionAfterDelete(self):
        if self.treeWidget.currentItem() is self.m_eventsItem:
            self.treeWidget.setCurrentItem(self.m_rpListItem, 0)
        self.editItem()

    def createCategories(self):
        self.m_rpListItem = QTreeWidgetItem(self.treeWidget, ["BONUSES"])
        self.treeWidget.addTopLevelItem(self.m_rpListItem)
        self.m_rpListItem.setSelected(True)
        self.m_rpListItem.setFlags(self.m_rpListItem.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)

        self.m_eventsItem = QTreeWidgetItem(self.treeWidget, ["EVENTS"])
        self.treeWidget.addTopLevelItem(self.m_eventsItem)
        self.m_eventsItem.setFlags(self.m_eventsItem.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsEditable)

        rootItem = self.treeWidget.invisibleRootItem()
        rootItem.setFlags(rootItem.flags() & ~Qt.ItemIsDropEnabled)

        font = QFont()
        font.setBold(True)
        font.setPointSize(int(font.pointSize() * 0.95))
        self.m_rpListItem.setFont(0, font)
        self.m_eventsItem.setFont(0, font)

        self.m_rpList = XkorRPList()
        self.editRPList.emit(self.m_rpList)
        self.updateEmptyState()  # the two categories don't go through listChanged

    def createItem(self, parent):
        item = QTreeWidgetItem(parent)
        self.treeWidget.setCurrentItem(item, 0)
        item.setFlags((item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)
        return item

    def editItem(self):
        if self.isInUse:
            return

        selection = self.treeWidget.selectedItems()

        if len(selection) == 1:
            item = selection[0]
            if item is self.m_rpListItem:
                self.editRPList.emit(self.m_rpList)
            elif self.m_events.get(parseAssignedUuid(item.data(0, Qt.UserRole))):
                # look up the event with the unique ID
                self.editEvent.emit(self.m_events[parseAssignedUuid(item.data(0, Qt.UserRole))])

    def events(self):
        self.updateEventNames()
        rval = []
        for i in range(self.m_eventsItem.childCount()):
            uniqueID = parseAssignedUuid(self.m_eventsItem.child(i).data(0, Qt.UserRole))
            rval.append((uniqueID, self.m_events.get(uniqueID)))
        return rval

    def initEvent(self, item):
        self.isInUse = True

        uniqueID = uuid.UUID(int=self.r._r.getrandbits(128))

        # create the actual event
        event = XkorEvent()
        self.m_events[uniqueID] = event

        item.setData(0, Qt.UserRole, uuidToString(uniqueID))
        self.isInUse = False

        self.editEvent.emit(event)

    def insertItem(self):
        self.isInUse = True
        selection = self.treeWidget.selectedItems()

        if len(selection) > 0:  # this operation is dangerous if there is no selection
            self.treeWidget.setCurrentItem(selection[0], 0, QItemSelectionModel.Clear)
        item = self.createItem(self.m_eventsItem)

        self.initEvent(item)

        self.initItem(item)
        self.treeWidget.editItem(item, 0)
        self.isInUse = False
        self.listChanged.emit()

    def reset(self):
        self.treeWidget.clear()

        self.m_rpList = XkorRPList()

        self.m_events.clear()

        self.createCategories()

    def rpList(self):
        return self.m_rpList

    def setEvents(self, events):
        for first, second in events:
            self.m_events[first] = second
            item = self.createItem(self.m_eventsItem)
            item.setText(0, second.name())
            item.setData(0, Qt.UserRole, uuidToString(first))
        self.treeWidget.setCurrentItem(self.m_rpListItem, 0)

    def setRPList(self, rpList):
        self.m_rpList = rpList
        self.treeWidget.setCurrentItem(self.m_rpListItem, 0)
        self.editRPList.emit(self.m_rpList)

    def updateButtons(self):
        selection = self.treeWidget.selectedItems()

        self.deleteAction.setEnabled(len(selection) > 0)

        if self.m_eventsItem and len(selection) == 1:
            # don’t delete or move the top-level items
            if selection[0].parent() is not self.m_eventsItem:
                self.deleteAction.setEnabled(False)
                self.moveUpAction.setEnabled(False)
                self.moveDownAction.setEnabled(False)
            else:
                # can only move up/down if we’re not at the top/bottom
                item = selection[0]

                canMoveUp = canMoveDown = True
                index = self.m_eventsItem.indexOfChild(item)
                if index == 0:  # top
                    canMoveUp = False
                if index == self.m_eventsItem.childCount() - 1:  # bottom
                    canMoveDown = False

                self.moveUpAction.setEnabled(canMoveUp)
                self.moveDownAction.setEnabled(canMoveDown)
        else:
            # can’t manipulate items if more than one is selected
            self.moveUpAction.setEnabled(False)
            self.moveDownAction.setEnabled(False)

    def updateEventNames(self):
        for i in range(self.m_eventsItem.childCount()):
            uniqueID = parseAssignedUuid(self.m_eventsItem.child(i).data(0, Qt.UserRole))
            if uniqueID in self.m_events:
                self.m_events[uniqueID].setName(self.m_eventsItem.child(i).text(0))
