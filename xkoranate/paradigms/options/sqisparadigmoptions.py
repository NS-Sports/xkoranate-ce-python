from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFormLayout, QLabel,
                               QRadioButton, QWidget)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toDouble, toString

from .collapsiblesection import XkorCollapsibleSection
from .constantspinbox import XkorConstantSpinBox

_DEFAULT_HOME_ADVANTAGE_MAGNITUDE = 4.0 / 3.0
_DEFAULT_CONSTANT_A = 0.1
_DEFAULT_CONSTANT_B = 0.07
_DEFAULT_ATTACKS = 12.0


class XkorSQISParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, defaultHomeAdvantageMagnitude=_DEFAULT_HOME_ADVANTAGE_MAGNITUDE,
                 defaultConstantA=_DEFAULT_CONSTANT_A, defaultConstantB=_DEFAULT_CONSTANT_B,
                 defaultAttacks=_DEFAULT_ATTACKS, parent=None):
        super().__init__(opts, parent)

        self.homeAdvantage = QCheckBox("Apply home advantage")
        if toString(self.options.get("homeAdvantage")) == "true":
            self.homeAdvantage.setCheckState(Qt.Checked)
        else:
            self.homeAdvantage.setCheckState(Qt.Unchecked)
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

        # SQIS formula constants: always active, no enable/disable toggle.
        self.constantA = XkorConstantSpinBox(
            toDouble(self.options.get("constantA", defaultConstantA)), defaultConstantA,
            decimals=3, minimum=-5.0, maximum=5.0, step=0.01)
        self.constantA.valueChanged.connect(self.setConstantA)
        self.setConstantA(self.constantA.value())

        self.constantB = XkorConstantSpinBox(
            toDouble(self.options.get("constantB", defaultConstantB)), defaultConstantB,
            decimals=3, minimum=-5.0, maximum=5.0, step=0.01)
        self.constantB.valueChanged.connect(self.setConstantB)
        self.setConstantB(self.constantB.value())

        self.attacks = XkorConstantSpinBox(
            toDouble(self.options.get("attacks", defaultAttacks)), defaultAttacks,
            decimals=0, minimum=1.0, maximum=100.0, step=1.0)
        self.attacks.valueChanged.connect(self.setAttacks)
        self.setAttacks(self.attacks.value())

        self.showTLAs = QCheckBox("Show team names")
        if toString(self.options.get("showTLAs", "true")) == "true":
            self.showTLAs.setCheckState(Qt.Checked)
        else:
            self.showTLAs.setCheckState(Qt.Unchecked)
        self.setShowTLAs(self.showTLAs.checkState())
        self.showTLAs.stateChanged.connect(self.setShowTLAs)

        # style modifiers box
        self.xkorStyleMods = QRadioButton("xkoranate-style (additive)")
        self.nsfsStyleMods = QRadioButton("NSFS3-style (multiplicative)")
        self.noStyleMods = QRadioButton("Disable style modifiers")
        if toString(self.options.get("styleMods")) != "false":
            self.xkorStyleMods.setChecked(True)
        elif toString(self.options.get("NSFSStyleMods")) == "true":
            self.nsfsStyleMods.setChecked(True)
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
        advancedForm.addRow("Constant A:", self.constantA)
        advancedForm.addRow("Constant B:", self.constantB)
        advancedForm.addRow("Attacks:", self.attacks)
        advancedForm.addRow(label, styleModsForm)

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

    def setConstantA(self, x):
        self.options["constantA"] = x
        self.optionsChanged.emit(self.options)

    def setConstantB(self, x):
        self.options["constantB"] = x
        self.optionsChanged.emit(self.options)

    def setAttacks(self, x):
        self.options["attacks"] = x
        self.optionsChanged.emit(self.options)

    def setShowTLAs(self, x):
        if Qt.CheckState(x) == Qt.Checked:
            self.options["showTLAs"] = "true"
        else:
            self.options["showTLAs"] = "false"
        self.optionsChanged.emit(self.options)

    def setStyleMods(self):
        checkedButton = self.styleMods.checkedButton()
        if checkedButton is self.xkorStyleMods:
            self.options["styleMods"] = "true"
            self.options["NSFSStyleMods"] = "false"
        elif checkedButton is self.nsfsStyleMods:
            self.options["styleMods"] = "false"
            self.options["NSFSStyleMods"] = "true"
        else:
            self.options["styleMods"] = "false"
            self.options["NSFSStyleMods"] = "false"
        self.optionsChanged.emit(self.options)
