from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from .abstracth2hparadigmoptions import XkorAbstractH2HParadigmOptions

_DEFAULT_HOME_ADVANTAGE_MAGNITUDE = 0.065


class XkorHowzzatParadigmOptions(XkorAbstractH2HParadigmOptions):
    def __init__(self, opts, defaultHomeAdvantageMagnitude=_DEFAULT_HOME_ADVANTAGE_MAGNITUDE, parent=None):
        super().__init__(opts, parent)

        self.homeAdvantage = self._flagCheckBox("homeAdvantage", "Apply home advantage",
                                                self._optionIsTrue("homeAdvantage"))

        self.homeAdvantageMagnitudeLabel = QLabel("Home advantage magnitude:")
        self.homeAdvantageMagnitude = self._constantSpinBox(
            "homeAdvantageMagnitude", defaultHomeAdvantageMagnitude,
            decimals=3, minimum=-1, maximum=1, step=0.005)
        self._enableWith(self.homeAdvantage, self.homeAdvantageMagnitudeLabel,
                         self.homeAdvantageMagnitude)

        self.useStyleMods = self._flagCheckBox("useStyleMods", "Apply style modifiers",
                                               self._optionIsTrue("useStyleMods", True))
        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))

        self.layout = self._checkBoxColumn(self.homeAdvantage, self.homeAdvantageMagnitude,
                                           self.useStyleMods, self.showTLAs)
        self.layout.addWidget(self.homeAdvantageMagnitudeLabel, 1, 0, Qt.AlignRight)
