from PySide6.QtWidgets import QFormLayout, QGridLayout, QLabel, QSpinBox

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toInt


def _placeSuffix(n):
    if n % 10 == 1 and n != 11:
        return "st"
    if n % 10 == 2 and n != 12:
        return "nd"
    if n % 10 == 3 and n != 13:
        return "rd"
    return "th"


class XkorCutoffOptions(XkorAbstractOptionsWidget):
    """How many advance ("all" at 0), over a line saying how ties are
    settled. Subclasses give the texts: cutoffText takes the place, e.g.
    "3rd", and initialText shows until the cutoff is changed."""

    cutoffLabel = ""
    initialText = ""
    noCutoffText = ""
    cutoffText = ""

    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.cutoff = QSpinBox()
        self.cutoff.setMinimum(0)
        self.cutoff.setMaximum(999)
        self.cutoff.setSpecialValueText("all")

        self.explanation = QLabel(self.initialText)
        self.explanation.setWordWrap(True)

        if "cutoff" in self.options:
            self.cutoff.setValue(toInt(self.options.get("cutoff")))
            self._explain(self.cutoff.value())
        self.cutoff.valueChanged.connect(self.setCutoff)

        form = QFormLayout()
        form.addRow(self.cutoffLabel, self.cutoff)

        layout = QGridLayout(self)
        layout.addLayout(form, 0, 0)
        layout.addWidget(self.explanation, 1, 0)

    def setCutoff(self, value):
        self._explain(value)
        self._setOption("cutoff", value)

    def _explain(self, value):
        if value == 0:
            self.explanation.setText(self.noCutoffText)
        else:
            self.explanation.setText(self.cutoffText % ("%d%s" % (value, _placeSuffix(value))))
