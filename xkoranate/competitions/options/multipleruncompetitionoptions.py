from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGridLayout, QSpinBox

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toInt


class XkorMultipleRunCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.runs = QSpinBox()
        self.runs.setValue(toInt(self.options.get("runs", 2)))
        self.runs.setRange(2, 99)
        self.runs.valueChanged.connect(lambda value: self._setOption("runs", value))

        self.sortResults = QCheckBox("Sort results")
        self.sortResults.setChecked(self._optionIsTrue("sortResults", default=True))
        self.sortResults.stateChanged.connect(self.setSortResults)

        self.sortByBestResult = self._flagCheckBox(
            "sortByBestResult", "Sort by best result when total result is tied",
            self._optionIsTrue("sortByBestResult", default=True), storeNow=False)
        self.sortByBestResult.setEnabled(self.sortResults.isChecked())

        form = QFormLayout()
        form.addRow("Runs:", self.runs)

        layout = QGridLayout(self)
        layout.addLayout(form, 0, 1)
        layout.addWidget(self.sortResults, 1, 1)
        layout.addWidget(self.sortByBestResult, 2, 1)
        layout.setHorizontalSpacing(0)
        if self._formAlignment() & Qt.AlignHCenter:
            # center the check boxes, but leave them left-aligned with each other on Mac OS
            layout.setColumnStretch(0, 1093)
            layout.setColumnStretch(2, 1093)

    def setSortResults(self, value):
        on = self._isChecked(value)
        self.options["sortResults"] = "true" if on else "false"
        self.sortByBestResult.setEnabled(on)
        if on:
            self._setFlag("sortByBestResult", self.sortByBestResult.checkState())
        else:
            self.options["sortByBestResult"] = "false"
        self.optionsChanged.emit(self.options)
