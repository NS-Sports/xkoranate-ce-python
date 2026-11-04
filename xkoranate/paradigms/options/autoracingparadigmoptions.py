from PySide6.QtWidgets import (QButtonGroup, QDoubleSpinBox, QFormLayout,
                               QGridLayout, QLabel, QRadioButton, QSpinBox)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toDouble, toInt, toString


class XkorAutoRacingParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.laps = QSpinBox()
        self.laps.setRange(1, 999)
        self.laps.setValue(toInt(self.options.get("laps", 50)))
        self.laps.valueChanged.connect(lambda x: self._setOption("laps", x))

        self.lapRecord = QDoubleSpinBox()
        self.lapRecord.setDecimals(3)
        self.lapRecord.setRange(0.001, 999.999)
        self.lapRecord.setValue(toDouble(self.options.get("lapRecord", 90)))
        self.lapRecord.valueChanged.connect(lambda x: self._setOption("lapRecord", x))

        self.lapVariance = QDoubleSpinBox()
        self.lapVariance.setDecimals(1)
        self.lapVariance.setRange(1, 99)
        self.lapVariance.setValue(toDouble(self.options.get("lapVariance", 15)))
        self.lapVariance.valueChanged.connect(lambda x: self._setOption("lapVariance", x))

        self.trackAcceleration = QDoubleSpinBox()
        self.trackAcceleration.setDecimals(1)
        self.trackAcceleration.setRange(0, 10)
        self.trackAcceleration.setValue(toDouble(self.options.get("trackAcceleration", 5)))
        self.trackAcceleration.setEnabled(False)
        self.trackAcceleration.valueChanged.connect(lambda x: self._setOption("trackAcceleration", x))

        self.trackCornering = QDoubleSpinBox()
        self.trackCornering.setDecimals(1)
        self.trackCornering.setRange(0, 10)
        self.trackCornering.setValue(toDouble(self.options.get("trackCornering", 5)))
        self.trackCornering.setEnabled(False)
        self.trackCornering.valueChanged.connect(lambda x: self._setOption("trackCornering", x))

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))
        self.useStartingGrid = self._flagCheckBox("useStartingGrid", "Use starting grid",
                                                  self._optionIsTrue("useStartingGrid"))

        # skill type box
        self.useSkill = QRadioButton("Single skill value")
        self.useACR = QRadioButton("Acceleration, cornering, and reliability")
        if toString(self.options.get("skillType")) != "attributes":
            self.useSkill.setChecked(True)
        else:
            self.useACR.setChecked(True)
        self.skillType = QButtonGroup()
        self.skillType.addButton(self.useSkill)
        self.skillType.addButton(self.useACR)
        self.skillType.idClicked.connect(self.setSkillType)

        skillTypeForm = QFormLayout()
        skillTypeForm.addRow(self.useSkill)
        skillTypeForm.addRow(self.useACR)

        # QFormLayout sucks, so we create our own label
        label = QLabel("Skill type:")
        label.setContentsMargins(0, -4, 0, 0)

        lapLayout = QGridLayout()
        lapLayout.addWidget(self.lapRecord, 0, 0)
        lapLayout.addWidget(QLabel("Variance:"), 0, 1)
        lapLayout.addWidget(self.lapVariance, 0, 2)
        lapLayout.setContentsMargins(0, 0, 0, 0)
        lapLayout.setColumnStretch(0, 1)
        lapLayout.setColumnStretch(1, 0)  # don't stretch the label
        lapLayout.setColumnStretch(2, 1)

        modifiersLayout = QGridLayout()
        modifiersLayout.addWidget(self.trackAcceleration, 0, 0)
        modifiersLayout.addWidget(QLabel("Cornering:"), 0, 1)
        modifiersLayout.addWidget(self.trackCornering, 0, 2)
        modifiersLayout.setContentsMargins(0, 0, 0, 0)
        modifiersLayout.setColumnStretch(0, 1)
        modifiersLayout.setColumnStretch(1, 0)  # don't stretch the label
        modifiersLayout.setColumnStretch(2, 1)

        form = QFormLayout(self)
        form.addRow("Number of laps:", self.laps)
        form.addRow("Lap record:", lapLayout)
        form.addRow(label, skillTypeForm)
        form.addRow("Acceleration:", modifiersLayout)
        form.addRow("", self.useStartingGrid)
        form.addRow("", self.showTLAs)

    def setSkillType(self):
        checkedButton = self.skillType.checkedButton()
        if checkedButton is self.useSkill:
            self.options["skillType"] = "skill"
            self.trackAcceleration.setEnabled(False)
            self.trackCornering.setEnabled(False)
        else:
            self.options["skillType"] = "attributes"
            self.trackAcceleration.setEnabled(True)
            self.trackCornering.setEnabled(True)

        self.optionsChanged.emit(self.options)
