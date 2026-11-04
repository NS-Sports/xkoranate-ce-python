from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorShortTrackParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionNotFalse("showTLAs"))
        self.allowAdvancement = self._flagCheckBox("allowAdvancement", "Allow athletes to be advanced",
                                                   self._optionNotFalse("allowAdvancement"))

        # layout
        layout = QGridLayout(self)
        layout.addWidget(self.showTLAs, 0, 1)
        layout.addWidget(self.allowAdvancement, 1, 1)
        layout.setHorizontalSpacing(0)
        if self._formAlignment() & Qt.AlignHCenter:
            # center the check boxes, but leave them left-aligned with each other on Mac OS
            layout.setColumnStretch(0, 1093)
            layout.setColumnStretch(2, 1093)
