from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from .collapsiblesection import XkorCollapsibleSection
from .abstracth2hparadigmoptions import XkorAbstractH2HParadigmOptions

_DEFAULT_HOME_ADVANTAGE_MAGNITUDE = 4.0 / 3.0
_DEFAULT_BASE_ATTACK_COEFF = 667.5
_DEFAULT_RANK_DIFF_MODIFIER = 12.0
_DEFAULT_RANK_COEFF = 31.5
_DEFAULT_RANK_SCALAR = 0.5
_DEFAULT_BASE_ATTACK_SUCCESS_THRESHOLD = 580.0
_DEFAULT_BASE_ATTACKS_SUPERIOR = 10.0
_DEFAULT_BASE_ATTACKS_INFERIOR = 10.0
_DEFAULT_ATTACK_COEFF_SUPERIOR = 10.0
_DEFAULT_ATTACK_COEFF_INFERIOR = 0.0


class XkorNSFSParadigmOptions(XkorAbstractH2HParadigmOptions):
    def __init__(self, opts, defaultHomeAdvantageMagnitude=_DEFAULT_HOME_ADVANTAGE_MAGNITUDE,
                 defaultBaseAttackCoeff=_DEFAULT_BASE_ATTACK_COEFF,
                 defaultRankDiffModifier=_DEFAULT_RANK_DIFF_MODIFIER,
                 defaultRankCoeff=_DEFAULT_RANK_COEFF, defaultRankScalar=_DEFAULT_RANK_SCALAR,
                 defaultBaseAttackSuccessThreshold=_DEFAULT_BASE_ATTACK_SUCCESS_THRESHOLD,
                 defaultBaseAttacksSuperior=_DEFAULT_BASE_ATTACKS_SUPERIOR,
                 defaultBaseAttacksInferior=_DEFAULT_BASE_ATTACKS_INFERIOR,
                 defaultAttackCoeffSuperior=_DEFAULT_ATTACK_COEFF_SUPERIOR,
                 defaultAttackCoeffInferior=_DEFAULT_ATTACK_COEFF_INFERIOR,
                 parent=None):
        super().__init__(opts, parent)

        self.homeAdvantage = self._flagCheckBox("homeAdvantage", "Apply home advantage",
                                                self._optionIsTrue("homeAdvantage"))

        self.homeAdvantageMagnitudeLabel = QLabel("Home advantage magnitude:")
        self.homeAdvantageMagnitude = self._constantSpinBox(
            "homeAdvantageMagnitude", defaultHomeAdvantageMagnitude,
            decimals=3, minimum=0, maximum=5, step=0.05)

        self._enableWith(self.homeAdvantage, self.homeAdvantageMagnitudeLabel,
                         self.homeAdvantageMagnitude)

        # NSFS formula constants (the sport file's own "NSFS parameters"
        # group): always active, no enable/disable toggle.
        self.baseAttackCoeff = self._constantSpinBox(
            "baseAttackCoeff", defaultBaseAttackCoeff,
            decimals=1, minimum=0.1, maximum=5000.0, step=5.0)
        self.rankDiffModifier = self._constantSpinBox(
            "rankDiffModifier", defaultRankDiffModifier,
            decimals=2, minimum=0.0, maximum=100.0, step=0.5)
        self.rankCoeff = self._constantSpinBox(
            "rankCoeff", defaultRankCoeff, decimals=2, minimum=0.0, maximum=500.0, step=0.5)
        self.rankScalar = self._constantSpinBox(
            "rankScalar", defaultRankScalar, decimals=3, minimum=0.0, maximum=5.0, step=0.05)
        self.baseAttackSuccessThreshold = self._constantSpinBox(
            "baseAttackSuccessThreshold", defaultBaseAttackSuccessThreshold,
            decimals=1, minimum=0.0, maximum=5000.0, step=5.0)
        self.baseAttacksSuperior = self._constantSpinBox(
            "baseAttacksSuperior", defaultBaseAttacksSuperior,
            decimals=0, minimum=0.0, maximum=100.0, step=1.0)
        self.baseAttacksInferior = self._constantSpinBox(
            "baseAttacksInferior", defaultBaseAttacksInferior,
            decimals=0, minimum=0.0, maximum=100.0, step=1.0)
        self.attackCoeffSuperior = self._constantSpinBox(
            "attackCoeffSuperior", defaultAttackCoeffSuperior,
            decimals=2, minimum=-100.0, maximum=100.0, step=0.5)
        self.attackCoeffInferior = self._constantSpinBox(
            "attackCoeffInferior", defaultAttackCoeffInferior,
            decimals=2, minimum=-100.0, maximum=100.0, step=0.5)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))

        styleModsLabel, styleModsForm = self._styleModsRow(preferNSFS=True)

        advancedContent = QWidget()
        advancedForm = QFormLayout(advancedContent)
        advancedForm.setContentsMargins(0, 4, 0, 0)
        advancedForm.addRow("Base attack coefficient:", self.baseAttackCoeff)
        advancedForm.addRow("Rank difference modifier:", self.rankDiffModifier)
        advancedForm.addRow("Rank coefficient:", self.rankCoeff)
        advancedForm.addRow("Rank scalar:", self.rankScalar)
        advancedForm.addRow("Base attack success threshold:", self.baseAttackSuccessThreshold)
        advancedForm.addRow("Base attacks (superior):", self.baseAttacksSuperior)
        advancedForm.addRow("Base attacks (inferior):", self.baseAttacksInferior)
        advancedForm.addRow("Attack coefficient (superior):", self.attackCoeffSuperior)
        advancedForm.addRow("Attack coefficient (inferior):", self.attackCoeffInferior)
        advancedForm.addRow(styleModsLabel, styleModsForm)

        # 10 rows once the formula constants joined style mods -- handled by
        # XkorCollapsibleSection's own height-capped scroll area
        self.advancedSection = XkorCollapsibleSection("Advanced options")
        self.advancedSection.setContent(advancedContent)

        form = QFormLayout(self)
        form.addRow("", self.homeAdvantage)
        form.addRow(self.homeAdvantageMagnitudeLabel, self.homeAdvantageMagnitude)
        form.addRow("", self.showTLAs)
        form.addRow(self.advancedSection)
