from PySide6.QtWidgets import QGridLayout

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorTimedParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionNotFalse("showTLAs"))

        # layout
        layout = QGridLayout(self)
        layout.addWidget(self.showTLAs, 0, 0, self._formAlignment())
