"""The circuit for a single Racing Scorinator race weekend.

One circuit's worth of the season calendar's columns, as a plain form rather
than a table, plus a switch for whether to run a practice session first.
"""

from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QFormLayout,
                               QGridLayout, QLabel, QLineEdit, QSpinBox)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.competitions.options.seasoncompetitionoptions import COLUMNS
from xkoranate.competitions.seasoncompetition import (QUALIFYING_FORMATS,
                                                     eventName)
from xkoranate.competitions.singleracecompetition import (DEFAULT_CIRCUIT,
                                                          SINGLE_RACE_KEYS)
from xkoranate.ui.fonts import XkorComboBox
from xkoranate.variant import toDouble, toString

# the same hover help the season calendar uses, keyed by the singular option
TOOLTIPS = {SINGLE_RACE_KEYS[key]: tip
            for key, _label, _type, tip in COLUMNS
            if SINGLE_RACE_KEYS[key] and tip}
TOOLTIPS["circuitEvent"] = ("What to call the race. Leave blank to call it "
                            "“Grand Prix of” the nation")


class XkorSingleRaceCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        form = QFormLayout()
        self._addRow(form, "Circuit:", "circuitName", self._text("circuitName"))
        self._addRow(form, "Nation:", "circuitNation",
                     self._text("circuitNation"))
        self._addRow(form, "Event name:", "circuitEvent", self._eventField())
        self._addRow(form, "Lap record (s):", "lapRecord",
                     self._spin("lapRecord", 1, 3600, 1, 3))
        self._addRow(form, "Track length (km):", "trackLength",
                     self._spin("trackLength", 0.1, 100, 0.25, 2))
        self._addRow(form, "Aggressiveness:", "aggressiveness",
                     self._spin("aggressiveness", 0, 10, 0.5, 1))
        self._addRow(form, "Technicality:", "technicality",
                     self._spin("technicality", 0, 10, 0.5, 1))
        self._addRow(form, "Qualifying:", "qualifyingFormat",
                     self._qualifyingBox())
        self._addRow(form, "Chance of rain (%):", "rainChance",
                     self._spin("rainChance", 0, 100, 1, 0))
        self._addRow(form, "Overtaking difficulty:", "overtakingDifficulty",
                     self._spin("overtakingDifficulty", 1, 5, 1, 1))
        self._addRow(form, "Error punishment:", "errorPunishment",
                     self._spin("errorPunishment", 1, 5, 1, 1))

        self.practice = QCheckBox("Run a practice session first")
        self.practice.setChecked(
            toString(self.options.get("includePractice", "N")).upper()[0:1] == "Y")
        self.practice.toggled.connect(
            lambda on: self.setOption("includePractice", "Y" if on else "N"))

        layout = QGridLayout(self)
        layout.addLayout(form, 0, 0)
        layout.addWidget(self.practice, 1, 0)
        layout.setContentsMargins(0, 0, 0, 0)

    def setOption(self, key, value):
        self.options[key] = value
        self.optionsChanged.emit(self.options)

    def _addRow(self, form, label, key, widget):
        """A labelled row whose label and field share the setting's hover help."""
        tip = TOOLTIPS.get(key, "")
        caption = QLabel(label)
        if tip:
            caption.setToolTip(tip)
            widget.setToolTip(tip)
        form.addRow(caption, widget)

    def _eventField(self):
        """Optional: a one-off can have a title of its own, and the placeholder
        shows the name it gets if it doesn't."""
        field = QLineEdit()
        field.setText(toString(self.options.get("circuitEvent", "")))
        field.setPlaceholderText(eventName(
            self.options.get("circuitNation", DEFAULT_CIRCUIT["circuitNation"])))
        field.editingFinished.connect(
            lambda f=field: self.setOption("circuitEvent", f.text().strip()))
        return field

    def _text(self, key):
        field = QLineEdit()
        field.setText(toString(self.options.get(key, DEFAULT_CIRCUIT[key])))
        field.editingFinished.connect(
            lambda k=key, f=field: self.setOption(k, f.text().strip()))
        return field

    def _spin(self, key, minimum, maximum, step, decimals):
        box = QDoubleSpinBox() if decimals else QSpinBox()
        if decimals:
            box.setDecimals(decimals)
            box.setSingleStep(step)
        box.setRange(minimum, maximum)
        box.setValue(toDouble(self.options.get(key, DEFAULT_CIRCUIT[key])))
        box.valueChanged.connect(lambda v, k=key: self.setOption(k, v))
        return box

    def _qualifyingBox(self):
        box = XkorComboBox()
        for label, value in QUALIFYING_FORMATS:
            box.addItem(label, value)
        current = toString(self.options.get("qualifyingFormat",
                                          DEFAULT_CIRCUIT["qualifyingFormat"]))
        index = box.findData(current)
        box.setCurrentIndex(index if index >= 0 else 0)
        box.currentIndexChanged.connect(
            lambda i, b=box: self.setOption("qualifyingFormat",
                                            toString(b.itemData(i))))
        return box
