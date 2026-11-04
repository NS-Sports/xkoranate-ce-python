from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorShortTrackParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionNotFalse("showTLAs"))
        self.allowAdvancement = self._flagCheckBox(
            "allowAdvancement", "Allow athletes to be advanced",
            self._optionNotFalse("allowAdvancement"))

        self._checkBoxColumn(self.showTLAs, self.allowAdvancement)
