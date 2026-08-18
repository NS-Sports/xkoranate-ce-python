import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidgetItem

from ..abstracttreewidget import XkorAbstractTreeWidget
from ..rng import Mt19937
from ..variant import toDouble


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


def _indexOf(l, value):
    # QStringList::indexOf semantics
    try:
        return l.index(value)
    except ValueError:
        return -1


# Column types whose displayed text represents a number, not a label.
_NUMERIC_COLUMN_TYPES = ("double", "skill", "golfStyle", "homeAdvantage")


class _AthleteTreeWidgetItem(QTreeWidgetItem):
    """QTreeWidgetItem that sorts numeric columns by value, not by text."""

    def __init__(self, treeWidget, columnTypes):
        super().__init__(treeWidget)
        self._tree = treeWidget
        self._columnTypes = columnTypes

    def __lt__(self, other):
        # Note: self.treeWidget() (the inherited accessor) must not be called
        # here -- doing so re-enters Qt's sort comparison and recurses forever.
        # Likewise, super().__lt__() dispatches virtually back to this same
        # override instead of Qt's default text comparison, so the "not
        # numeric" case is reimplemented directly below instead of delegated.
        column = max(self._tree.sortColumn(), 0)
        if (column < len(self._columnTypes)
                and self._columnTypes[column] in _NUMERIC_COLUMN_TYPES):
            return toDouble(self.text(column)) < toDouble(other.text(column))
        return self.text(column) < other.text(column)


class XkorAbstractAthleteWidget(XkorAbstractTreeWidget):
    itemDeleted = Signal(object)  # QUuid
    signupListDirectoryChanged = Signal(str)

    def __init__(self, columnKeys, columnNames, columnTypes, minDouble, maxDouble, doubleStep):
        self.r = Mt19937()  # std::tr1::mt19937 member
        super().__init__()
        self.m_columnKeys = list(columnKeys)
        self.m_columnNames = list(columnNames)
        self.m_columnTypes = list(columnTypes)
        self.m_minDouble = minDouble
        self.m_maxDouble = maxDouble
        self.m_doubleStep = doubleStep

    def createItem(self):
        item = _AthleteTreeWidgetItem(self.treeWidget, self.m_columnTypes)
        self.treeWidget.setCurrentItem(item, 0)
        item.setFlags((item.flags() | Qt.ItemIsEditable) & ~Qt.ItemIsDropEnabled)
        return item

    def initItem(self, item, athleteName="", id=None, nation="", skill=0, properties=None):
        # C++ overloads: the no-argument form generates a fresh random ID
        raise NotImplementedError  # pure virtual

    def deleteItems(self):
        selection = self.treeWidget.selectedItems()
        for i in selection:
            self.itemDeleted.emit(_uuidFromString(i.data(_indexOf(self.m_columnKeys, "name"), Qt.UserRole)))
        XkorAbstractTreeWidget.deleteItems(self)

    def athletes(self):
        raise NotImplementedError  # pure virtual

    def setAthletes(self, athletes):
        raise NotImplementedError  # pure virtual

    def setMaxRank(self, newMax):
        raise NotImplementedError  # pure virtual

    def setMinRank(self, newMin):
        raise NotImplementedError  # pure virtual
