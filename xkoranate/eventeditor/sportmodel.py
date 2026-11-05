from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

SPORT_NAME = Qt.UserRole + 93
SPORT_DATA = Qt.UserRole + 984


class XkorSportModel(QStandardItemModel):
    def findSport(self, fullName):
        root = self.invisibleRootItem()
        for i in range(root.rowCount()):
            child = root.child(i)
            if child and child.data(SPORT_NAME) == fullName:
                return child.index()
            for j in range(child.rowCount()):
                grandchild = child.child(j)
                if grandchild and grandchild.data(SPORT_NAME) == fullName:
                    return grandchild.index()
                for k in range(grandchild.rowCount()):
                    greatGrandchild = grandchild.child(k)
                    if greatGrandchild and greatGrandchild.data(SPORT_NAME) == fullName:
                        return greatGrandchild.index()
        return QModelIndex()

    def initItem(self, item, sport):
        item.setData(sport.name(), SPORT_NAME)
        item.setData(sport, SPORT_DATA)

    def insertSport(self, s):
        # find or create the discipline item
        disciplineItem = None
        root = self.invisibleRootItem()
        for i in range(root.rowCount()):
            if root.child(i) and root.child(i).text() == s.discipline():
                disciplineItem = root.child(i)
        if not disciplineItem:
            disciplineItem = QStandardItem(s.discipline())
            disciplineItem.setEditable(False)
            if s.event() == "":
                self.initItem(disciplineItem, s)
            root.appendRow(disciplineItem)

        # find or create the event item
        if s.event() != "":
            eventItem = None
            for i in range(disciplineItem.rowCount()):
                if disciplineItem.child(i) and disciplineItem.child(i).text() == s.event():
                    eventItem = disciplineItem.child(i)
            if not eventItem:
                eventItem = QStandardItem(s.event())
                eventItem.setEditable(False)
                if s.scorinator() == "":
                    self.initItem(eventItem, s)
                disciplineItem.appendRow(eventItem)

            # create the scorinator item
            if s.scorinator() != "":
                scorinatorItem = QStandardItem(s.scorinator())
                scorinatorItem.setEditable(False)
                self.initItem(scorinatorItem, s)
                eventItem.appendRow(scorinatorItem)
