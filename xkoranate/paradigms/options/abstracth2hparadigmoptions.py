from PySide6.QtWidgets import QButtonGroup, QFormLayout, QLabel, QRadioButton

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toString


class XkorAbstractH2HParadigmOptions(XkorAbstractOptionsWidget):
    """Pieces shared by the head-to-head paradigms' options widgets."""

    def _enableWith(self, checkBox, *widgets):
        """Keep `widgets` enabled only while `checkBox` is ticked."""
        def update(state):
            enabled = self._isChecked(state)
            for widget in widgets:
                widget.setEnabled(enabled)

        update(checkBox.checkState())
        checkBox.stateChanged.connect(update)

    def _styleModsRow(self, preferNSFS):
        """The "Style modifiers:" label and its three radio buttons, as a
        (label, layout) form row. Each paradigm defaults to its own style:
        with `preferNSFS` the NSFS3 flag is read first and counts as on
        unless it is "false"; otherwise the xkoranate flag is."""
        self.xkorStyleMods = QRadioButton("xkoranate-style (additive)")
        self.nsfsStyleMods = QRadioButton("NSFS3-style (multiplicative)")
        self.noStyleMods = QRadioButton("Disable style modifiers")
        preferred = [("styleMods", self.xkorStyleMods), ("NSFSStyleMods", self.nsfsStyleMods)]
        if preferNSFS:
            preferred.reverse()
        (firstKey, firstButton), (secondKey, secondButton) = preferred
        if toString(self.options.get(firstKey)) != "false":
            firstButton.setChecked(True)
        elif toString(self.options.get(secondKey)) == "true":
            secondButton.setChecked(True)
        else:
            self.noStyleMods.setChecked(True)
        self.styleMods = QButtonGroup()
        self.styleMods.addButton(self.xkorStyleMods)
        self.styleMods.addButton(self.nsfsStyleMods)
        self.styleMods.addButton(self.noStyleMods)
        self.styleMods.idClicked.connect(self.setStyleMods)

        styleModsForm = QFormLayout()
        styleModsForm.addRow(self.xkorStyleMods)
        styleModsForm.addRow(self.nsfsStyleMods)
        styleModsForm.addRow(self.noStyleMods)

        # QFormLayout sucks, so we create our own label
        label = QLabel("Style modifiers:")
        label.setContentsMargins(0, -4, 0, 0)
        return label, styleModsForm

    def setStyleMods(self):
        checkedButton = self.styleMods.checkedButton()
        self.options["styleMods"] = "true" if checkedButton is self.xkorStyleMods else "false"
        self.options["NSFSStyleMods"] = "true" if checkedButton is self.nsfsStyleMods else "false"
        self.optionsChanged.emit(self.options)
