from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFormLayout, QLabel,
                               QRadioButton, QWidget)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toDouble, toString

from .collapsiblesection import XkorCollapsibleSection
from .constantspinbox import XkorConstantSpinBox

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


class XkorNSFSParadigmOptions(XkorAbstractOptionsWidget):
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

        self.homeAdvantage = QCheckBox("Apply home advantage")
        if toString(self.options.get("homeAdvantage")) == "true":
            self.homeAdvantage.setCheckState(Qt.Checked)
        self.setHomeAdvantage(self.homeAdvantage.checkState())
        self.homeAdvantage.stateChanged.connect(self.setHomeAdvantage)

        self.homeAdvantageMagnitudeLabel = QLabel("Home advantage magnitude:")
        self.homeAdvantageMagnitude = XkorConstantSpinBox(
            toDouble(self.options.get("homeAdvantageMagnitude", defaultHomeAdvantageMagnitude)),
            defaultHomeAdvantageMagnitude, decimals=3, minimum=0, maximum=5, step=0.05)
        self.homeAdvantageMagnitude.valueChanged.connect(self.setHomeAdvantageMagnitude)
        self.setHomeAdvantageMagnitude(self.homeAdvantageMagnitude.value())

        self._updateHomeAdvantageMagnitudeEnabled(self.homeAdvantage.checkState())
        self.homeAdvantage.stateChanged.connect(self._updateHomeAdvantageMagnitudeEnabled)

        # NSFS formula constants (the sport file's own "NSFS parameters"
        # group): always active, no enable/disable toggle.
        self.baseAttackCoeff = XkorConstantSpinBox(
            toDouble(self.options.get("baseAttackCoeff", defaultBaseAttackCoeff)), defaultBaseAttackCoeff,
            decimals=1, minimum=0.1, maximum=5000.0, step=5.0)
        self.baseAttackCoeff.valueChanged.connect(self.setBaseAttackCoeff)
        self.setBaseAttackCoeff(self.baseAttackCoeff.value())

        self.rankDiffModifier = XkorConstantSpinBox(
            toDouble(self.options.get("rankDiffModifier", defaultRankDiffModifier)), defaultRankDiffModifier,
            decimals=2, minimum=0.0, maximum=100.0, step=0.5)
        self.rankDiffModifier.valueChanged.connect(self.setRankDiffModifier)
        self.setRankDiffModifier(self.rankDiffModifier.value())

        self.rankCoeff = XkorConstantSpinBox(
            toDouble(self.options.get("rankCoeff", defaultRankCoeff)), defaultRankCoeff,
            decimals=2, minimum=0.0, maximum=500.0, step=0.5)
        self.rankCoeff.valueChanged.connect(self.setRankCoeff)
        self.setRankCoeff(self.rankCoeff.value())

        self.rankScalar = XkorConstantSpinBox(
            toDouble(self.options.get("rankScalar", defaultRankScalar)), defaultRankScalar,
            decimals=3, minimum=0.0, maximum=5.0, step=0.05)
        self.rankScalar.valueChanged.connect(self.setRankScalar)
        self.setRankScalar(self.rankScalar.value())

        self.baseAttackSuccessThreshold = XkorConstantSpinBox(
            toDouble(self.options.get(
                "baseAttackSuccessThreshold", defaultBaseAttackSuccessThreshold)),
            defaultBaseAttackSuccessThreshold,
            decimals=1, minimum=0.0, maximum=5000.0, step=5.0)
        self.baseAttackSuccessThreshold.valueChanged.connect(self.setBaseAttackSuccessThreshold)
        self.setBaseAttackSuccessThreshold(self.baseAttackSuccessThreshold.value())

        self.baseAttacksSuperior = XkorConstantSpinBox(
            toDouble(self.options.get("baseAttacksSuperior", defaultBaseAttacksSuperior)),
            defaultBaseAttacksSuperior,
            decimals=0, minimum=0.0, maximum=100.0, step=1.0)
        self.baseAttacksSuperior.valueChanged.connect(self.setBaseAttacksSuperior)
        self.setBaseAttacksSuperior(self.baseAttacksSuperior.value())

        self.baseAttacksInferior = XkorConstantSpinBox(
            toDouble(self.options.get("baseAttacksInferior", defaultBaseAttacksInferior)),
            defaultBaseAttacksInferior,
            decimals=0, minimum=0.0, maximum=100.0, step=1.0)
        self.baseAttacksInferior.valueChanged.connect(self.setBaseAttacksInferior)
        self.setBaseAttacksInferior(self.baseAttacksInferior.value())

        self.attackCoeffSuperior = XkorConstantSpinBox(
            toDouble(self.options.get("attackCoeffSuperior", defaultAttackCoeffSuperior)),
            defaultAttackCoeffSuperior,
            decimals=2, minimum=-100.0, maximum=100.0, step=0.5)
        self.attackCoeffSuperior.valueChanged.connect(self.setAttackCoeffSuperior)
        self.setAttackCoeffSuperior(self.attackCoeffSuperior.value())

        self.attackCoeffInferior = XkorConstantSpinBox(
            toDouble(self.options.get("attackCoeffInferior", defaultAttackCoeffInferior)),
            defaultAttackCoeffInferior,
            decimals=2, minimum=-100.0, maximum=100.0, step=0.5)
        self.attackCoeffInferior.valueChanged.connect(self.setAttackCoeffInferior)
        self.setAttackCoeffInferior(self.attackCoeffInferior.value())

        self.showTLAs = QCheckBox("Show team names")
        if toString(self.options.get("showTLAs", "true")) == "true":
            self.showTLAs.setCheckState(Qt.Checked)
        self.setShowTLAs(self.showTLAs.checkState())
        self.showTLAs.stateChanged.connect(self.setShowTLAs)

        # style modifiers options
        self.xkorStyleMods = QRadioButton("xkoranate-style (additive)")
        self.nsfsStyleMods = QRadioButton("NSFS3-style (multiplicative)")
        self.noStyleMods = QRadioButton("Disable style modifiers")
        if toString(self.options.get("NSFSStyleMods")) != "false":
            self.nsfsStyleMods.setChecked(True)
        elif toString(self.options.get("styleMods")) == "true":
            self.xkorStyleMods.setChecked(True)
        else:
            self.noStyleMods.setChecked(True)
        self.styleMods = QButtonGroup()
        self.styleMods.addButton(self.xkorStyleMods)
        self.styleMods.addButton(self.nsfsStyleMods)
        self.styleMods.addButton(self.noStyleMods)
        self.styleMods.idClicked.connect(self.setStyleMods)

        styleModsForm = QFormLayout()
        styleModsForm.addRow(self.xkorStyleMods)
        styleModsForm.addRow(self.nsfsStyleMods)
        styleModsForm.addRow(self.noStyleMods)

        # QFormLayout sucks, so we create our own label
        label = QLabel("Style modifiers:")
        label.setContentsMargins(0, -4, 0, 0)

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
        advancedForm.addRow(label, styleModsForm)

        # 10 rows once the formula constants joined style mods -- handled by
        # XkorCollapsibleSection's own height-capped scroll area
        self.advancedSection = XkorCollapsibleSection("Advanced options")
        self.advancedSection.setContent(advancedContent)

        form = QFormLayout(self)
        form.addRow("", self.homeAdvantage)
        form.addRow(self.homeAdvantageMagnitudeLabel, self.homeAdvantageMagnitude)
        form.addRow("", self.showTLAs)
        form.addRow(self.advancedSection)

    def setHomeAdvantage(self, x):
        if Qt.CheckState(x) == Qt.Checked:
            self.options["homeAdvantage"] = "true"
        else:
            self.options["homeAdvantage"] = "false"
        self.optionsChanged.emit(self.options)

    def setHomeAdvantageMagnitude(self, x):
        self.options["homeAdvantageMagnitude"] = x
        self.optionsChanged.emit(self.options)

    def _updateHomeAdvantageMagnitudeEnabled(self, x):
        enabled = Qt.CheckState(x) == Qt.Checked
        self.homeAdvantageMagnitudeLabel.setEnabled(enabled)
        self.homeAdvantageMagnitude.setEnabled(enabled)

    def setBaseAttackCoeff(self, x):
        self.options["baseAttackCoeff"] = x
        self.optionsChanged.emit(self.options)

    def setRankDiffModifier(self, x):
        self.options["rankDiffModifier"] = x
        self.optionsChanged.emit(self.options)

    def setRankCoeff(self, x):
        self.options["rankCoeff"] = x
        self.optionsChanged.emit(self.options)

    def setRankScalar(self, x):
        self.options["rankScalar"] = x
        self.optionsChanged.emit(self.options)

    def setBaseAttackSuccessThreshold(self, x):
        self.options["baseAttackSuccessThreshold"] = x
        self.optionsChanged.emit(self.options)

    def setBaseAttacksSuperior(self, x):
        self.options["baseAttacksSuperior"] = x
        self.optionsChanged.emit(self.options)

    def setBaseAttacksInferior(self, x):
        self.options["baseAttacksInferior"] = x
        self.optionsChanged.emit(self.options)

    def setAttackCoeffSuperior(self, x):
        self.options["attackCoeffSuperior"] = x
        self.optionsChanged.emit(self.options)

    def setAttackCoeffInferior(self, x):
        self.options["attackCoeffInferior"] = x
        self.optionsChanged.emit(self.options)

    def setShowTLAs(self, x):
        if Qt.CheckState(x) == Qt.Checked:
            self.options["showTLAs"] = "true"
        else:
            self.options["showTLAs"] = "false"
        self.optionsChanged.emit(self.options)

    def setStyleMods(self):
        checkedButton = self.styleMods.checkedButton()
        if checkedButton is self.nsfsStyleMods:
            self.options["styleMods"] = "false"
            self.options["NSFSStyleMods"] = "true"
        elif checkedButton is self.xkorStyleMods:
            self.options["styleMods"] = "true"
            self.options["NSFSStyleMods"] = "false"
        else:
            self.options["styleMods"] = "false"
            self.options["NSFSStyleMods"] = "false"
        self.optionsChanged.emit(self.options)
