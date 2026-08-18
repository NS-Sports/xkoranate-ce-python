import time
import uuid

from PySide6.QtCore import QDir, Qt
from PySide6.QtWidgets import QFileDialog, QHeaderView, QTreeWidgetItemIterator

from ..athlete import XkorAthlete
from ..icons import icon_action
from ..ui.dialogs import resolved_search_path
from ..ui.fonts import column_width_for
from ..variant import qNumber, toDouble, toString
from .abstractathletewidget import (_AthleteTreeWidgetItem,
                                    XkorAbstractAthleteWidget, _indexOf,
                                    _uuidFromString, _uuidToString)
from .athletedelegate import XkorAthleteDelegate


class XkorAthleteWidget(XkorAbstractAthleteWidget):
    def __init__(self, columnKeys, columnNames, columnTypes, minDouble=0, maxDouble=0, doubleStep=1):
        super().__init__(columnKeys, columnNames, columnTypes, minDouble, maxDouble, doubleStep)
        self.init()

    def init(self):
        self.r.seed(int(time.time()))
        self.dialog = None
        self.m_homeAdvantageDefault = 0.0

        self.delegate = XkorAthleteDelegate(self.m_columnTypes, self.m_minDouble,
                                            self.m_maxDouble, self.m_doubleStep)

        self.treeWidget.setColumnCount(len(self.m_columnKeys))
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.setItemDelegate(self.delegate)
        self.treeWidget.sortItems(0, Qt.AscendingOrder)
        self.treeWidget.setHeaderLabels(self.m_columnNames)
        self.treeWidget.header().setStretchLastSection(False)

        # set the column widths
        for i in range(len(self.m_columnTypes)):
            if self.m_columnTypes[i] in ("double", "golfStyle", "skill", "homeAdvantage"):
                self.treeWidget.header().setSectionResizeMode(i, QHeaderView.Fixed)
                self.treeWidget.header().resizeSection(i, column_width_for(self.treeWidget, "8888.88"))
            else:
                self.treeWidget.header().setSectionResizeMode(i, QHeaderView.Stretch)

        self.importAction = icon_action("document-import", "Import from text file", self)
        self.importAction.setEnabled(True)
        self.importAction.triggered.connect(lambda: self.importAthletes())

        actions = [self.insertAction, self.deleteAction, None, self.importAction]
        self.setupLayout(actions)

    def insertionText(self):
        return "Add participant"

    def deletionText(self):
        return "Remove participants"

    def athletes(self):
        rval = []
        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            item = i.value()
            a = XkorAthlete()
            a.name = item.text(_indexOf(self.m_columnKeys, "name"))
            a.id = _uuidFromString(item.data(_indexOf(self.m_columnKeys, "name"), Qt.UserRole))
            a.nation = item.text(_indexOf(self.m_columnKeys, "nation"))
            a.skill = toDouble(item.text(_indexOf(self.m_columnKeys, "skill")))
            for j in self.m_columnKeys:
                a.setProperty(j, item.text(_indexOf(self.m_columnKeys, j)))
            rval.append(a)
            i += 1
        return rval

    def importAthletes(self, filename=None):
        # C++ overloads: importAthletes() shows the dialog; importAthletes(QString) reads
        if filename is None:
            if self.dialog:
                self.dialog.deleteLater()

            self.dialog = QFileDialog(self)
            self.dialog.setWindowTitle("Open semicolon-delimited participant file")
            self.dialog.setNameFilter("Text files (*.txt)")
            self.dialog.setWindowModality(Qt.WindowModal)
            self.dialog.setAcceptMode(QFileDialog.AcceptOpen)

            self.dialog.setDirectory(resolved_search_path("signupLists"))
            self.dialog.fileSelected.connect(self.importAthletes)
            self.dialog.open()
            return

        self.isInUse = True

        if filename != "":
            try:
                f = open(filename, "r", encoding="utf-8")
            except OSError:
                return

            with f:
                for line in f.read().splitlines():
                    l = line.split(";")
                    if len(l) >= 3:
                        athleteName = l[0].strip()
                        athleteNation = l[1].strip()
                        athleteSkill = l[2].strip()

                        # any columns beyond name/nation/skill (e.g. style
                        # mods) are matched positionally to the paradigm's
                        # extra column keys
                        properties = {}
                        for i in range(3, min(len(l), len(self.m_columnKeys))):
                            properties[self.m_columnKeys[i]] = l[i].strip()

                        self.initItem(self.createItem(), athleteName,
                                      uuid.UUID(int=self.r._r.getrandbits(128)),
                                      athleteNation, toDouble(athleteSkill), properties)

            path = QDir(filename)
            path.cdUp()
            self.signupListDirectoryChanged.emit(path.canonicalPath())

        self.isInUse = False
        self.listChanged.emit()

    def initItem(self, item, athleteName="", id=None, nation="", skill=0, properties=None):
        if id is None:
            # the no-argument C++ overload generates a fresh random ID
            id = uuid.UUID(int=self.r._r.getrandbits(128))
        if properties is None:
            properties = {}

        item.setText(_indexOf(self.m_columnKeys, "name"), athleteName)
        item.setData(_indexOf(self.m_columnKeys, "name"), Qt.UserRole, _uuidToString(id))
        item.setText(_indexOf(self.m_columnKeys, "nation"), nation)
        item.setText(_indexOf(self.m_columnKeys, "skill"), qNumber(skill))
        item.setTextAlignment(_indexOf(self.m_columnKeys, "skill"), Qt.AlignRight)
        for i in range(len(self.m_columnTypes)):
            if self.m_columnKeys[i] in properties:
                item.setText(i, toString(properties[self.m_columnKeys[i]]))
                if self.m_columnTypes[i] in ("double", "skill", "homeAdvantage"):
                    item.setTextAlignment(i, Qt.AlignRight)
            elif self.m_columnTypes[i] == "double":
                item.setText(i, "0")
                item.setTextAlignment(i, Qt.AlignRight)
            elif self.m_columnTypes[i] == "homeAdvantage":
                # the paradigm sets this to whatever an unset rating should
                # mean for its own current mode (see setHomeAdvantageDefault)
                item.setText(i, qNumber(self.m_homeAdvantageDefault))
                item.setTextAlignment(i, Qt.AlignRight)

    def setAthletes(self, athletes):
        self.treeWidget.clear()
        for i in athletes:
            item = _AthleteTreeWidgetItem(self.treeWidget, self.m_columnTypes)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.initItem(item, i.name, i.id, i.nation, i.skill, i.properties)
        self.listChanged.emit()

    def setMaxRank(self, newMax):
        self.delegate.setMaxRank(newMax)

    def setMinRank(self, newMin):
        self.delegate.setMinRank(newMin)

    def setHomeAdvantageDefault(self, value):
        self.m_homeAdvantageDefault = value
