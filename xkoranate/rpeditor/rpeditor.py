import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QDoubleSpinBox,
                               QFormLayout, QGridLayout, QHBoxLayout,
                               QMessageBox, QRadioButton, QVBoxLayout,
                               QWidget)

from ..ui.dialogs import message_box
from ..ui.fonts import XkorComboBox
from ..variant import toString
from .rpbonuswidgets.olympicrpbonuswidget import XkorOlympicRPBonusWidget
from .rpbonuswidgets.wc36rpbonuswidget import XkorWC36RPBonusWidget


class XkorRPEditor(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.m_data = None
        self.isLoading = False
        self.m_currentRPCalcType = ""
        self.m_currentFileName = ""

        self.m_useTeamBonus = QRadioButton("Teams")
        self.m_useParticipantBonus = QRadioButton("Participants")
        self.m_useTeamBonus.setChecked(True)
        self.bonusStyle = QButtonGroup()
        self.bonusStyle.addButton(self.m_useTeamBonus)
        self.bonusStyle.addButton(self.m_useParticipantBonus)
        self.m_useTeamBonus.toggled.connect(self.setDataChanged)
        self.m_useParticipantBonus.toggled.connect(self.setDataChanged)

        assignBonusesTo = QGridLayout()
        assignBonusesTo.addWidget(self.m_useTeamBonus, 0, 0)
        assignBonusesTo.addWidget(self.m_useParticipantBonus, 0, 1)
        assignBonusesTo.setColumnStretch(0, 0)  # don’t stretch the left column
        assignBonusesTo.setColumnStretch(1, 1)

        self.m_bonusEffect = QDoubleSpinBox()
        self.m_bonusEffect.setMinimum(0)
        self.m_bonusEffect.setMaximum(100)
        self.m_bonusEffect.setSingleStep(1)
        self.m_bonusEffect.setSuffix("%")
        self.m_bonusEffect.setDecimals(1)
        self.m_bonusEffect.setValue(15)
        self.m_bonusEffect.valueChanged.connect(self.setDataChanged)

        self.m_rpCalcType = XkorComboBox()
        self.m_rpCalcType.addItem("Absolute", "olympic")
        self.m_rpCalcType.addItem("Relative", "relative")
        self.m_rpCalcType.addItem("World Cup 36", "wc36")

        # tree widget
        self.m_rpBonus = XkorOlympicRPBonusWidget()
        self.m_useTeamBonus.toggled.connect(self.m_rpBonus.setUseTeamBonus)
        self.m_useParticipantBonus.toggled.connect(self.m_rpBonus.setUseParticipantBonus)

        # form layout
        rpForm = QFormLayout()
        rpForm.addRow("Assign bonuses to:", assignBonusesTo)
        rpForm.addRow("Effect of bonus:", self.m_bonusEffect)
        rpForm.addRow("Bonus formula:", self.m_rpCalcType)

        # tree widget layout
        self.m_bonusLayout = QHBoxLayout()
        self.m_bonusLayout.addWidget(self.m_rpBonus)

        # RP bonus group
        rpLayout = QVBoxLayout(self)
        rpLayout.addLayout(rpForm, 0)
        rpLayout.addLayout(self.m_bonusLayout, 1)

        self.m_rpCalcType.currentIndexChanged.connect(self.setDataChanged)
        self.m_rpCalcType.currentIndexChanged.connect(self.updateRPBonusWidget)
        self.m_rpBonus.listChanged.connect(self.setDataChanged)

    def setData(self, data):
        self.isLoading = True  # prevent dataChanged from being emitted
        if data is not None:
            self.updateData()  # we want to save any edits to the previous signup list (if any)

            if data.useTeams():
                self.m_useTeamBonus.setChecked(True)
            else:
                self.m_useParticipantBonus.setChecked(True)
            self.m_bonusEffect.setValue(data.rpEffect())
            self.m_rpCalcType.setCurrentIndex(self.m_rpCalcType.findData(data.rpCalculationType()))
            self.updateRPBonusWidget()
            self.m_rpBonus.setBonuses(data.bonuses())
            self.m_rpBonus.setOptions(data.rpOptions())
            self.m_rpBonus.setMaxBonus(data.maxBonus())
            self.m_rpBonus.setMinBonus(data.minBonus())
        else:
            print("Null pointer in XkorRPEditor::setData(XkorRPList *)", file=sys.stderr)
        self.m_data = data
        self.isLoading = False  # allow dataChanged to be emitted if the user does stuff

    def setDataChanged(self):
        if not self.isLoading:
            self.dataChanged.emit()

    def updateData(self):
        if self.m_data is not None:
            self.m_data.setUseTeams(self.m_useTeamBonus.isChecked())
            self.m_data.setRPEffect(self.m_bonusEffect.value())
            self.m_data.setRPCalculationType(toString(self.m_rpCalcType.itemData(self.m_rpCalcType.currentIndex())))
            self.m_data.setBonuses(self.m_rpBonus.bonuses())
            self.m_data.setRPOptions(self.m_rpBonus.options())
            self.m_data.setMaxBonus(self.m_rpBonus.maxBonus())
            self.m_data.setMinBonus(self.m_rpBonus.minBonus())
        else:
            print("Null pointer in XkorRPEditor::updateData()", file=sys.stderr)

    def updateRPBonusWidget(self):
        newRPCalcType = toString(self.m_rpCalcType.itemData(self.m_rpCalcType.currentIndex()))
        if self.m_currentRPCalcType != newRPCalcType:
            if len(self.m_rpBonus.bonuses()) > 0:
                warning = message_box(
                    self, "Are you sure you want to reset all bonuses by changing the bonus formula?",
                    QMessageBox.Ok | QMessageBox.Cancel,
                    informativeText="If you change the bonus formula, all of your bonuses will be lost.",
                    defaultButton=QMessageBox.Cancel, escapeButton=QMessageBox.Cancel,
                    destructiveButton=QMessageBox.Ok)
                r = warning.exec()
                if r == QMessageBox.Cancel:
                    self.m_rpCalcType.setCurrentIndex(self.m_rpCalcType.findData(self.m_currentRPCalcType))
                    return

            self.m_bonusLayout.removeWidget(self.m_rpBonus)
            self.m_rpBonus.setParent(None)  # delete m_rpBonus
            self.m_rpBonus.deleteLater()
            if newRPCalcType == "wc36":
                self.m_rpBonus = XkorWC36RPBonusWidget()
            else:
                self.m_rpBonus = XkorOlympicRPBonusWidget()

            self.updateData()
            if self.m_data is not None and not self.m_data.useTeams():
                self.m_rpBonus.setUseParticipantBonus()
            else:
                self.m_rpBonus.setUseTeamBonus()

            self.m_rpBonus.listChanged.connect(self.setDataChanged)
            self.m_useTeamBonus.toggled.connect(self.m_rpBonus.setUseTeamBonus)
            self.m_useParticipantBonus.toggled.connect(self.m_rpBonus.setUseParticipantBonus)
            self.m_bonusLayout.addWidget(self.m_rpBonus)
            self.m_currentRPCalcType = newRPCalcType
