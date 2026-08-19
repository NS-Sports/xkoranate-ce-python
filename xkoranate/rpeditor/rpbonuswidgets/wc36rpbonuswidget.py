from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QFormLayout, QGridLayout, QHeaderView, QSpinBox,
                               QStyle, QToolBar, QTreeWidgetItemIterator)

from ...ui.fonts import column_width_for
from ...variant import qNumber, toDouble, toInt
from ..abstractrpbonuswidget import XkorAbstractRPBonusWidget
from .wc36rpbonusdelegate import XkorWC36RPBonusDelegate


class XkorWC36RPBonusWidget(XkorAbstractRPBonusWidget):
    def __init__(self):
        super().__init__()
        # matchday box
        self.matchday = QSpinBox()
        self.matchday.valueChanged.connect(self.setListChanged)

        self.matchdayForm = QFormLayout()
        self.matchdayForm.addRow("Current matchday:", self.matchday)

        self.treeWidget.setColumnCount(3)
        self.treeWidget.setSortingEnabled(True)
        self._delegate = XkorWC36RPBonusDelegate()
        self.treeWidget.setItemDelegate(self._delegate)
        self.treeWidget.sortItems(0, Qt.AscendingOrder)
        self.setUseTeamBonus()

        # set the column widths — "Exceptional" is the widest level label
        self.treeWidget.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.treeWidget.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.treeWidget.header().resizeSection(1, column_width_for(self.treeWidget, "Exceptional"))
        self.treeWidget.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.treeWidget.header().resizeSection(2, column_width_for(self.treeWidget, "8888.88"))

        self.setupLayout()

    def insertionText(self):
        return "Add nation"

    def deletionText(self):
        return "Remove nations"

    def bonuses(self):
        rval = {}
        i = QTreeWidgetItemIterator(self.treeWidget)
        while i.value():
            item = i.value()
            properties = {}
            bestRPLevel = toDouble(item.data(1, 1093))
            quantity = toDouble(item.text(2))
            properties["bestRPLevel"] = bestRPLevel
            properties["quantity"] = quantity
            properties["bonus"] = self.calculateBonus(bestRPLevel, quantity)
            rval[item.text(0)] = properties
            i += 1
        return rval

    def calculateBonus(self, bestRPLevel, quantity):
        rpMultiplier = (bestRPLevel + 1) * bestRPLevel / 2 + 1
        quantityMultiplier = 0
        if quantity >= self.matchday.value() // 2:  # integer division, as in the C++
            quantityMultiplier = 1.4
        elif quantity > 0:
            quantityMultiplier = 1
        return rpMultiplier * quantityMultiplier

    def initItem(self, item, nation="", bestRPLevel=0, quantity=0):
        item.setText(0, nation)
        item.setText(1, self.levelToString(bestRPLevel))
        item.setData(1, 1093, bestRPLevel)
        item.setText(2, qNumber(quantity))

    def levelToString(self, level):
        if level == 4:
            return "Exceptional"
        elif level == 3:
            return "Great"
        elif level == 2:
            return "Good"
        elif level == 1:
            return "Poor"
        else:
            return "Slani"

    def maxBonus(self):
        return 15.4

    def options(self):
        rval = {"matchday": self.matchday.value()}
        return rval

    def setBonuses(self, bonuses):
        self.clear()
        for key, value in bonuses.items():
            self.initItem(self.createItem(), key,
                          value.get("bestRPLevel", 0.0), value.get("quantity", 0.0))
        self.listChanged.emit()

    def setupLayout(self):
        # tool bar
        toolBar = QToolBar()
        small = self.style().pixelMetric(QStyle.PM_SmallIconSize)
        toolBar.setIconSize(QSize(small, small))
        toolBar.addAction(self.insertAction)
        toolBar.addAction(self.deleteAction)

        self.layout = QGridLayout(self)
        self.layout.addLayout(self.matchdayForm, 0, 0)
        self.layout.addWidget(self.treeWidget, 1, 0)
        self.layout.addWidget(toolBar, 2, 0, Qt.AlignCenter)

        self.layout.setContentsMargins(0, 0, 0, 0)

    def setListChanged(self):
        self.listChanged.emit()

    def setOptions(self, options):
        self.matchday.setValue(toInt(options.get("matchday")))

    def setUseParticipantBonus(self, use=True):
        if use:
            self.treeWidget.setHeaderLabels(["Participant", "Level", "Quantity"])

    def setUseTeamBonus(self, use=True):
        if use:
            self.treeWidget.setHeaderLabels(["Team", "Level", "Quantity"])
