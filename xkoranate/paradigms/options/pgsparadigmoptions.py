from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QGridLayout

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toDouble


class XkorPGSParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionNotFalse("showTLAs"))

        self.maxScore = QDoubleSpinBox()
        self.maxScore.setRange(0, 1.5)
        self.maxScore.setSingleStep(0.01)
        self.maxScore.setValue(toDouble(self.options.get("maxScore", 1.5)))
        self.maxScore.valueChanged.connect(lambda x: self._setOption("maxScore", x))

        form = QFormLayout()
        form.addRow("Maximum score after first run:", self.maxScore)

        layout = QGridLayout(self)
        layout.addWidget(self.showTLAs, 0, 0, self._formAlignment())
        layout.addLayout(form, 1, 0)
