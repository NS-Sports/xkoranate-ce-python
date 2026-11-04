from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorH2HParadigmOptions(XkorAbstractOptionsWidget):
    """Pieces shared by the head-to-head paradigms' options widgets."""

    def _enableWith(self, checkBox, *widgets):
        """Keep `widgets` enabled only while `checkBox` is ticked."""
        def update(state):
            enabled = self._isChecked(state)
            for widget in widgets:
                widget.setEnabled(enabled)

        update(checkBox.checkState())
        checkBox.stateChanged.connect(update)
