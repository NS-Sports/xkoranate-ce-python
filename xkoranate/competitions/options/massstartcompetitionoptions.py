from PySide6.QtWidgets import QCheckBox

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorMassStartCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.overallRanking = self._flagCheckBox(
            "overallRanking", "Show overall ranking across all groups",
            self._optionIsTrue("overallRanking"), storeNow=False)

        self.sortResults = QCheckBox("Sort results")
        self.sortResults.setChecked(self._optionIsTrue("sortResults", default=True))
        self.sortResults.stateChanged.connect(self.setSortResults)

        self._checkBoxColumn(self.sortResults, self.overallRanking)

    def setSortResults(self, value):
        on = self._isChecked(value)
        self.options["sortResults"] = "true" if on else "false"
        self.overallRanking.setEnabled(on)
        if on:
            self._setFlag("overallRanking", self.overallRanking.checkState())
        else:
            self.options["overallRanking"] = "false"
        self.optionsChanged.emit(self.options)
