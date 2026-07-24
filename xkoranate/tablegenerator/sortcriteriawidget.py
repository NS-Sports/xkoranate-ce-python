from PySide6.QtWidgets import QAbstractItemView, QTreeWidgetItemIterator

from ..abstracttreewidget import XkorAbstractTreeWidget
from ..variant import toString
from .sortcriteriadelegate import XkorSortCriteriaDelegate


class XkorSortCriteriaWidget(XkorAbstractTreeWidget):
    def __init__(self):
        super().__init__()
        self.sortTypes = ["awayGoals", "goalAverage", "goalDifference",
                          "goalsAgainst", "goalsFor", "h2hAwayGoals",
                          "h2hGoalDifference", "h2hGoalsAgainst",
                          "h2hGoalsFor", "h2hPoints", "h2hWins", "otWins",
                          "points", "regulationWins",
                          "winPercent", "winPercentPure", "winPercentNFL",
                          "wins"]
        self.sortNames = ["Away goals", "Goal average", "Goal difference",
                          "Goals against", "Goals for",
                          "Head-to-head away goals",
                          "Head-to-head goal difference",
                          "Head-to-head goals against",
                          "Head-to-head goals for", "Head-to-head points",
                          "Head-to-head wins", "Overtime/shootout wins",
                          "Points", "Regulation wins",
                          "Win percentage (draws count 50%)",
                          "Win percentage (draws count 0%)",
                          "Win percentage (draws ignored)", "Wins"]

        self.treeWidget.setColumnCount(1)
        # C++ allocates the delegate without a parent; pass the tree widget as
        # parent here so the delegate is kept alive on the Python side
        self.treeWidget.setItemDelegate(
            XkorSortCriteriaDelegate(self.sortTypes, self.sortNames, self.treeWidget))
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setDragDropMode(QAbstractItemView.InternalMove)

        actions = []
        actions.append(self.insertAction)
        actions.append(self.deleteAction)
        self.setupLayout(actions, True)  # vertical bar

    def insertionText(self):
        return "Add sort criterion"

    def deletionText(self):
        return "Remove sort criteria"

    def movingUpText(self):
        return "Move criterion up"

    def movingDownText(self):
        return "Move criterion down"

    @staticmethod
    def defaultSortCriteria():
        rval = []
        rval.append("points")
        rval.append("goalDifference")
        rval.append("goalsFor")
        rval.append("h2hPoints")
        rval.append("h2hGoalDifference")
        rval.append("h2hGoalsFor")
        return rval

    def initItem(self, item, sortType=""):
        item.setData(0, 1093, sortType)

        # get the name of the sort type
        n = self.sortTypes.index(sortType) if sortType in self.sortTypes else -1
        if 0 <= n < len(self.sortNames):
            item.setText(0, self.sortNames[n])
        else:
            item.setText(0, "<unknown sort type %s>" % sortType)

    def sortCriteria(self):
        rval = []
        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            rval.append(toString(i.value().data(0, 1093)))
            i += 1
        return rval

    def setSortCriteria(self, sc):
        self.isInUse = True
        self.treeWidget.clear()
        for i in sc:
            self.initItem(self.createItem(), i)
        self.isInUse = False
        self.listChanged.emit()
