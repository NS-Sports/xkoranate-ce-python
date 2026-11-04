from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QStyle, QWidget)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toDouble

_DEFAULT_HOME_ADVANTAGE_MAGNITUDE = 0.065


class XkorFootba11erParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, defaultHomeAdvantageMagnitude=_DEFAULT_HOME_ADVANTAGE_MAGNITUDE, parent=None):
        super().__init__(opts, parent)
        self._defaultHomeAdvantageMagnitude = defaultHomeAdvantageMagnitude

        self.homeAdvantage = self._flagCheckBox("homeAdvantage", "Apply home advantage",
                                                self._optionIsTrue("homeAdvantage"))

        self.homeAdvantageMagnitudeLabel = QLabel("Home advantage magnitude:")
        self.homeAdvantageMagnitude = QDoubleSpinBox()
        self.homeAdvantageMagnitude.setDecimals(3)
        self.homeAdvantageMagnitude.setRange(-1, 1)
        self.homeAdvantageMagnitude.setSingleStep(0.005)
        self.homeAdvantageMagnitude.setValue(toDouble(self.options.get(
            "homeAdvantageMagnitude", defaultHomeAdvantageMagnitude)))
        self.setHomeAdvantageMagnitude(self.homeAdvantageMagnitude.value())
        self.homeAdvantageMagnitude.valueChanged.connect(self.setHomeAdvantageMagnitude)

        self.restoreHomeAdvantageMagnitude = QPushButton("Restore default")
        self.restoreHomeAdvantageMagnitude.setToolTip(
            "Reset to this sport's configured value (%.3f)" % defaultHomeAdvantageMagnitude)
        self.restoreHomeAdvantageMagnitude.clicked.connect(self._restoreHomeAdvantageMagnitude)

        self._updateHomeAdvantageMagnitudeEnabled(self.homeAdvantage.checkState())
        self.homeAdvantage.stateChanged.connect(self._updateHomeAdvantageMagnitudeEnabled)

        homeAdvantageMagnitudeRow = QWidget()
        homeAdvantageMagnitudeRowLayout = QHBoxLayout(homeAdvantageMagnitudeRow)
        homeAdvantageMagnitudeRowLayout.setContentsMargins(0, 0, 0, 0)
        homeAdvantageMagnitudeRowLayout.addWidget(self.homeAdvantageMagnitude)
        homeAdvantageMagnitudeRowLayout.addWidget(self.restoreHomeAdvantageMagnitude)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.homeAdvantage, 0, 1)
        self.layout.addWidget(self.homeAdvantageMagnitudeLabel, 1, 0, Qt.AlignRight)
        self.layout.addWidget(homeAdvantageMagnitudeRow, 1, 1)
        self.layout.addWidget(self.showTLAs, 2, 1)
        self.layout.setHorizontalSpacing(0)
        if Qt.AlignmentFlag(self.style().styleHint(QStyle.SH_FormLayoutFormAlignment)) & Qt.AlignHCenter:
            # center the check boxes, but leave them left-aligned with each other on Mac OS
            self.layout.setColumnStretch(0, 1093)
            self.layout.setColumnStretch(2, 1093)

    def setHomeAdvantageMagnitude(self, x):
        self.options["homeAdvantageMagnitude"] = x
        self.optionsChanged.emit(self.options)

    def _restoreHomeAdvantageMagnitude(self):
        self.homeAdvantageMagnitude.setValue(self._defaultHomeAdvantageMagnitude)

    def _updateHomeAdvantageMagnitudeEnabled(self, x):
        enabled = Qt.CheckState(x) == Qt.Checked
        self.homeAdvantageMagnitudeLabel.setEnabled(enabled)
        self.homeAdvantageMagnitude.setEnabled(enabled)
        self.restoreHomeAdvantageMagnitude.setEnabled(enabled)
