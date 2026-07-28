"""The season calendar for The Racing Scorinator.

One row per race week, mirroring the circuit block on the sheet's Input tab.
A row's type decides what the week is worth: "Race" weeks get qualifying and a
race, "Testing" weeks get a practice session and no points. The number of
filled-in rows is what sets the competition's matchday count.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QGridLayout, QHeaderView, QItemDelegate, QLabel,
                               QLineEdit, QTableWidget, QTableWidgetItem)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.competitions.seasoncompetition import (CHOICES, DEFAULT_CALENDAR,
                                                     NEW_WEEK, choiceLabel,
                                                     choiceValue)
from xkoranate.ui.fonts import XkorComboBox
from xkoranate.variant import toDouble, toList, toString

# key, header, type, tooltip ("" for a column whose name says it all)
COLUMNS = (
    ("circuitNations", "NAT", "string",
     "The host nation. Its drivers and teams get the home bonus, and the week "
     "is titled “Grand Prix of” it"),
    ("circuitNames", "Circuit", "string",
     "Naming a circuit is what makes the row a race week; clear it to drop the "
     "week"),
    ("circuitTypes", "Type", "choice",
     "“Race” for qualifying and a race; “Testing” for a practice session only, "
     "scoring nothing"),
    ("lapRecords", "Lap record (s)", "double",
     "The circuit's lap record in seconds. Every lap time is built up from it"),
    ("trackLengths", "Length (km)", "double",
     "Lap length. The race distance divided by this gives the lap count"),
    ("aggressiveness", "A", "double",
     "How much the circuit rewards a driver's aggression, 1–10"),
    ("technicality", "T", "double",
     "How much the circuit rewards a driver's technique, 1–10"),
    ("qualifyingFormats", "Qualifying", "choice",
     "Traditional (best of three laps), one shot, two tiers (top ten run "
     "again) or four elimination sessions"),
    ("rainChances", "Rain %", "double",
     "Chance of anything wetter than cloudy. Rain slows every car down"),
    ("overtakingDifficulties", "Overtaking", "double",
     "1 easy to 5 hard. Higher makes a poor grid slot cost more time"),
    ("errorPunishments", "Errors", "double",
     "1 forgiving to 5 treacherous. Higher makes a spin cost more time"),
)

KEYS = [c[0] for c in COLUMNS]
NAME_COLUMN = KEYS.index("circuitNames")

EXTRA_ROWS = 6  # blank rows so the calendar can be extended in place
MINIMUM_ROWS = 24  # room to type a whole season into an empty calendar


class _CalendarDelegate(QItemDelegate):
    """Edits the fixed-choice columns with a dropdown, rather than leaving the
    user to remember how the format codes are spelled."""

    def createEditor(self, parent, option, index):
        key, _label, type, _tip = COLUMNS[index.column()]
        if type != "choice":
            editor = QLineEdit(parent)
            editor.setFrame(False)
            return editor
        box = XkorComboBox(parent)
        for shown, stored in CHOICES[key]:
            box.addItem(shown, stored)
        return box

    def setEditorData(self, editor, index):
        key, _label, type, _tip = COLUMNS[index.column()]
        text = toString(index.model().data(index, Qt.DisplayRole))
        if type != "choice":
            editor.setText(text)
            return
        # match on the stored value, so a hand-edited "TT" still selects
        position = editor.findData(choiceValue(key, text))
        editor.setCurrentIndex(position if position >= 0 else 0)

    def setModelData(self, editor, model, index):
        _key, _label, type, _tip = COLUMNS[index.column()]
        if type != "choice":
            model.setData(index, editor.text())
        else:
            model.setData(index, editor.currentText())


class XkorSeasonCompetitionOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.isFilling = False
        rows = max([len(toList(self.options.get(key, DEFAULT_CALENDAR[key])))
                    for key, _label, _type, _tip in COLUMNS]
                   + [MINIMUM_ROWS - EXTRA_ROWS]) + EXTRA_ROWS

        self.calendar = QTableWidget(rows, len(COLUMNS))
        self.calendar.setHorizontalHeaderLabels([c[1] for c in COLUMNS])
        self.calendar.setVerticalHeaderLabels(
            ["Week %d" % (i + 1) for i in range(rows)])
        self.calendar.setGridStyle(Qt.NoPen)
        self.calendar.setAlternatingRowColors(True)
        self.calendar.setItemDelegate(_CalendarDelegate(self.calendar))

        header = self.calendar.horizontalHeader()
        for index, (_key, _label, type, _tip) in enumerate(COLUMNS):
            header.setSectionResizeMode(
                index, QHeaderView.Stretch if type == "string" else QHeaderView.ResizeToContents)
        metrics = QFontMetrics(QFont())
        self.calendar.verticalHeader().setDefaultSectionSize(metrics.height() + 2)

        # hover help on the column names that aren't self-explanatory
        headerItem = self.calendar.horizontalHeaderItem
        for index, (_key, _label, _type, tip) in enumerate(COLUMNS):
            if tip and headerItem(index) is not None:
                headerItem(index).setToolTip(tip)

        for column, (key, _label, type, _tip) in enumerate(COLUMNS):
            values = toList(self.options.get(key, DEFAULT_CALENDAR[key]))
            for row in range(min(len(values), rows)):
                text = (choiceLabel(key, values[row]) if type == "choice"
                        else toString(values[row]))
                self.calendar.setItem(row, column, QTableWidgetItem(text))

        self.calendar.cellChanged.connect(self.updateData)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Race weeks. Naming a circuit adds the week; "
                                "clearing the name drops it."), 0, 0)
        layout.addWidget(self.calendar, 1, 0)
        layout.setContentsMargins(0, 0, 0, 0)

    def _fillNewWeek(self, row):
        """A freshly named circuit gets the neutral race-week settings, so the
        row is a working race the moment it exists and the numbers are there to
        be seen and edited rather than implied."""
        self.isFilling = True
        try:
            for index, (key, _label, type, _tip) in enumerate(COLUMNS):
                if key not in NEW_WEEK:
                    continue
                cell = self.calendar.item(row, index)
                if cell is not None and cell.text().strip():
                    continue
                text = (choiceLabel(key, NEW_WEEK[key]) if type == "choice"
                        else toString(NEW_WEEK[key]))
                if cell is None:
                    self.calendar.setItem(row, index, QTableWidgetItem(text))
                else:
                    cell.setText(text)
        finally:
            self.isFilling = False

    def updateData(self, row, column):
        if self.isFilling:
            return  # our own default-filling, not the user typing

        # every column is rewritten on any edit: the lists are parallel, so
        # naming a new circuit has to lengthen all of them at once
        weeks = [i for i in range(self.calendar.rowCount())
                 if self.calendar.item(i, NAME_COLUMN) is not None
                 and self.calendar.item(i, NAME_COLUMN).text().strip() != ""]
        if column == NAME_COLUMN and row in weeks:
            self._fillNewWeek(row)

        for index, (key, _label, type, _tip) in enumerate(COLUMNS):
            values = []
            for i in weeks:
                cell = self.calendar.item(i, index)
                text = cell.text().strip() if cell is not None else ""
                if type == "double":
                    values.append(toDouble(text))
                elif type == "choice":
                    values.append(choiceValue(key, text))
                else:
                    values.append(text)
            self.options[key] = values

        self.optionsChanged.emit(self.options)
