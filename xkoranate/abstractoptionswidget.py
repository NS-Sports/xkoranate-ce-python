from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QStyle, QWidget

from xkoranate.variant import toDouble, toString


class XkorAbstractOptionsWidget(QWidget):
    optionsChanged = Signal(dict)

    def __init__(self, opts, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.options = dict(opts)

    def getOptions(self):
        return dict(self.options)

    def setOptions(self, newOptions):
        self.options = dict(newOptions)
        self.optionsChanged.emit(self.options)

    # --- shared helpers for subclasses ------------------------------------

    def _setOption(self, key, value):
        """Store one option and announce the change."""
        self.options[key] = value
        self.optionsChanged.emit(self.options)

    @staticmethod
    def _isChecked(state):
        """True for Qt.Checked, whether given as a Qt.CheckState or as the
        plain int that QCheckBox.stateChanged sends."""
        if isinstance(state, Qt.CheckState):
            state = state.value
        return state == Qt.CheckState.Checked.value

    def _setFlag(self, key, state):
        """Store a check box state as the string "true" or "false"."""
        self._setOption(key, "true" if self._isChecked(state) else "false")

    def _optionIsTrue(self, key, default=False):
        """Is options[key] the string "true"? A missing key counts as
        `default`."""
        return toString(self.options.get(key, "true" if default else "false")) == "true"

    def _optionNotFalse(self, key):
        """Is options[key] anything but "false"? A missing key counts as on."""
        return toString(self.options.get(key)) != "false"

    def _flagCheckBox(self, key, label, checked, storeNow=True):
        """A check box kept in sync with options[key] as "true"/"false".

        `checked` is the starting state; callers decide it with
        _optionIsTrue / _optionNotFalse so each keeps its own reading of
        odd stored values. With `storeNow` the starting state is written
        back straight away, which normalises the stored value. Connect any
        extra stateChanged slots after this returns: they then run after
        the option is stored, as before."""
        box = QCheckBox(label)
        box.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        if storeNow:
            self._setFlag(key, box.checkState())
        box.stateChanged.connect(lambda state: self._setFlag(key, state))
        return box

    def _constantSpinBox(self, key, default, **spinArgs):
        """A formula-constant spin box with a 'Restore default' button,
        kept in sync with options[key]. `default` is the sport's value;
        spinArgs go to XkorConstantSpinBox (decimals, minimum, maximum,
        step)."""
        from xkoranate.paradigms.options.constantspinbox import XkorConstantSpinBox

        box = XkorConstantSpinBox(toDouble(self.options.get(key, default)), default, **spinArgs)
        box.valueChanged.connect(lambda value: self._setOption(key, value))
        self._setOption(key, box.value())
        return box

    def _formAlignment(self):
        return Qt.AlignmentFlag(self.style().styleHint(QStyle.StyleHint.SH_FormLayoutFormAlignment))

    def _checkBoxColumn(self, *boxes):
        """Lay check boxes out one per row in column 1 of a new grid on this
        widget. Where the platform centres forms, the column is centred as
        a block; the boxes stay left-aligned with each other (as on macOS).
        Returns the layout."""
        layout = QGridLayout(self)
        for row, box in enumerate(boxes):
            layout.addWidget(box, row, 1)
        layout.setHorizontalSpacing(0)
        if self._formAlignment() & Qt.AlignHCenter:
            layout.setColumnStretch(0, 1093)
            layout.setColumnStretch(2, 1093)
        return layout
