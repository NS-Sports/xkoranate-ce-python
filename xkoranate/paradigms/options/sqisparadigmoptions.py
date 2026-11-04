from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from .collapsiblesection import XkorCollapsibleSection
from .abstracth2hparadigmoptions import XkorAbstractH2HParadigmOptions

_DEFAULT_HOME_ADVANTAGE_MAGNITUDE = 4.0 / 3.0
_DEFAULT_CONSTANT_A = 0.1
_DEFAULT_CONSTANT_B = 0.07
_DEFAULT_ATTACKS = 12.0


class XkorSQISParadigmOptions(XkorAbstractH2HParadigmOptions):
    def __init__(self, opts, defaultHomeAdvantageMagnitude=_DEFAULT_HOME_ADVANTAGE_MAGNITUDE,
                 defaultConstantA=_DEFAULT_CONSTANT_A, defaultConstantB=_DEFAULT_CONSTANT_B,
                 defaultAttacks=_DEFAULT_ATTACKS, parent=None):
        super().__init__(opts, parent)

        self.homeAdvantage = self._flagCheckBox("homeAdvantage", "Apply home advantage",
                                                self._optionIsTrue("homeAdvantage"))

        self.homeAdvantageMagnitudeLabel = QLabel("Home advantage magnitude:")
        self.homeAdvantageMagnitude = self._constantSpinBox(
            "homeAdvantageMagnitude", defaultHomeAdvantageMagnitude,
            decimals=3, minimum=0, maximum=5, step=0.05)

        self._enableWith(self.homeAdvantage, self.homeAdvantageMagnitudeLabel,
                         self.homeAdvantageMagnitude)

        # SQIS formula constants: always active, no enable/disable toggle.
        self.constantA = self._constantSpinBox(
            "constantA", defaultConstantA, decimals=3, minimum=-5.0, maximum=5.0, step=0.01)
        self.constantB = self._constantSpinBox(
            "constantB", defaultConstantB, decimals=3, minimum=-5.0, maximum=5.0, step=0.01)
        self.attacks = self._constantSpinBox(
            "attacks", defaultAttacks, decimals=0, minimum=1.0, maximum=100.0, step=1.0)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))

        styleModsLabel, styleModsForm = self._styleModsRow(preferNSFS=False)

        advancedContent = QWidget()
        advancedForm = QFormLayout(advancedContent)
        advancedForm.setContentsMargins(0, 4, 0, 0)
        advancedForm.addRow("Constant A:", self.constantA)
        advancedForm.addRow("Constant B:", self.constantB)
        advancedForm.addRow("Attacks:", self.attacks)
        advancedForm.addRow(styleModsLabel, styleModsForm)

        self.advancedSection = XkorCollapsibleSection("Advanced options")
        self.advancedSection.setContent(advancedContent)

        form = QFormLayout(self)
        form.addRow("", self.homeAdvantage)
        form.addRow(self.homeAdvantageMagnitudeLabel, self.homeAdvantageMagnitude)
        form.addRow("", self.showTLAs)
        form.addRow(self.advancedSection)
