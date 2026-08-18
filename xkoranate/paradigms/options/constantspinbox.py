from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QPushButton, QWidget


class XkorConstantSpinBox(QWidget):
    """A QDoubleSpinBox plus a 'Restore default' button, for a per-event
    override of a paradigm formula constant whose default comes from the
    sport file. Every paradigm options widget already builds this exact row
    by hand for its home-advantage magnitude; this factors that out so
    exposing additional formula constants (LISA's REAR/power scalar/margin
    divisor, SQIS's constantA/B, NSFS's rank/attack coefficients, etc.)
    doesn't mean re-wiring the same spinbox+button dance each time."""

    valueChanged = Signal(float)

    def __init__(self, value, default, decimals=3, minimum=0.0, maximum=9999.0,
                 step=0.1, parent=None):
        super().__init__(parent)
        self._default = default

        self.spinBox = QDoubleSpinBox()
        self.spinBox.setDecimals(decimals)
        self.spinBox.setRange(minimum, maximum)
        self.spinBox.setSingleStep(step)
        self.spinBox.setValue(value)
        self.spinBox.valueChanged.connect(self.valueChanged)

        self.restoreButton = QPushButton("Restore default")
        self.restoreButton.setToolTip(
            "Reset to this sport's configured value (%s)" % (("%%.%df" % decimals) % default))
        self.restoreButton.clicked.connect(self._restore)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spinBox)
        layout.addWidget(self.restoreButton)

    def value(self):
        return self.spinBox.value()

    def setValue(self, value):
        self.spinBox.setValue(value)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.spinBox.setEnabled(enabled)
        self.restoreButton.setEnabled(enabled)

    def _restore(self):
        self.spinBox.setValue(self._default)
