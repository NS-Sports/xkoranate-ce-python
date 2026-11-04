from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from ...ui.fonts import column_width_for
from ...variant import qNumber, toDouble
from ..abstractrpbonuswidget import XkorAbstractRPBonusWidget
from .olympicrpbonusdelegate import XkorOlympicRPBonusDelegate


class XkorOlympicRPBonusWidget(XkorAbstractRPBonusWidget):
    def __init__(self):
        super().__init__()
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setSortingEnabled(True)
        self._delegate = XkorOlympicRPBonusDelegate()
        self.treeWidget.setItemDelegate(self._delegate)
        self.treeWidget.sortItems(0, Qt.AscendingOrder)
        self.setUseTeamBonus()

        # set the column widths
        self.treeWidget.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.treeWidget.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.treeWidget.header().resizeSection(1, column_width_for(self.treeWidget, "8888.88"))

        actions = [self.insertAction, self.deleteAction]
        self.setupLayout(actions)

    def insertionText(self):
        return "Add nation"

    def deletionText(self):
        return "Remove nations"

    def bonuses(self):
        rval = {}
        for item in self.iterItems():
            properties = {"bonus": toDouble(item.text(1))}
            rval[item.text(0)] = properties
        return rval

    def initItem(self, item, nation="", bonus=0):
        item.setText(0, nation)
        item.setText(1, qNumber(bonus))

    def setBonuses(self, bonuses):
        self.clear()
        for key, value in bonuses.items():
            self.initItem(self.createItem(), key, value.get("bonus", 0.0))
        self.listChanged.emit()

    def setUseParticipantBonus(self, use=True):
        if use:
            self.treeWidget.setHeaderLabels(["Participant", "Bonus"])

    def setUseTeamBonus(self, use=True):
        if use:
            self.treeWidget.setHeaderLabels(["Team", "Bonus"])
