from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorNSFSGridironParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.usePeriods = self._flagCheckBox("usePeriods", "Show period-by-period results",
                                             self._optionIsTrue("usePeriods", True))
        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))

        self._checkBoxColumn(self.usePeriods, self.showTLAs)
