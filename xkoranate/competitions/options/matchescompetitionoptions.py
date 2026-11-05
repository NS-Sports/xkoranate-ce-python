from PySide6.QtWidgets import QGridLayout

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorMatchesCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.allowDraws = self._flagCheckBox("allowDraws", "Allow draws", self._optionNotFalse("allowDraws"),
                                             storeNow=False)

        layout = QGridLayout(self)
        layout.addWidget(self.allowDraws, 0, 0, self._formAlignment())
