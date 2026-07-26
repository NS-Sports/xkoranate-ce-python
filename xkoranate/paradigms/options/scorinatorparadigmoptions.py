"""Season settings for The Racing Scorinator.

The sheet keeps these in the block to the right of its Input tab — race
distance, the dice constants and the points table. The teams, tyre makers and
engine makers that block also holds are entrants rather than settings, so they
live on the participants step instead (XkorScorinatorParticipantsWidget).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QDoubleSpinBox, QFormLayout,
                               QGridLayout, QHeaderView, QLabel, QLineEdit,
                               QSpinBox, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.paradigms.scorinatorparadigm import DEFAULTS, defaultValue
from xkoranate.ui.fonts import XkorComboBox
from xkoranate.variant import toDouble, toInt, toList, toString

# label, key, tooltip — the tooltip explains anything whose name doesn't
TOOLTIPS = {
    "kmPerRace": "Race distance. Divided by a circuit's length to get its lap "
                 "count",
    "speedPercent": "Scales every lap record: below 100% the cars are slower "
                    "than the record, above it they are faster",
    "driversOnGrid": "How many cars start. Drivers who qualify outside this "
                     "many are classified DNS",
    "safetyCar": "A real safety car closes the field up behind the leader; a "
                 "virtual one just adds a fixed delay to everyone",
    "polePositionBonus": "Championship points for taking pole, on top of the "
                         "finishing points",
    "fastestLapBonus": "Championship points for the fastest lap of the race",
    "useTyres": "Turn off to ignore tyre makers entirely, whatever is on the "
                "participants list",
    "useEngines": "Turn off to ignore engine makers entirely, whatever is on "
                  "the participants list",
    "showQuarterDistances": "Print the running order after each quarter of the "
                            "race distance",
    "alliances": "Nations that share a driver pool. A driver from either one "
                 "gets half the home bonus at the other's race. Comma-"
                 "separated, e.g. AAA+BBB, CCC+DDD",
    "spinConstant": "Higher means more spins. Compared against a dice roll of "
                    "0–90, less the driver's reliability times the multiplier",
    "spinMultiplier": "How much reliability protects against spinning. Higher "
                      "favours reliable drivers",
    "crashConstant": "Higher means more retirements. Compared against a dice "
                     "roll of 0–81",
    "crashMultiplier": "How much reliability protects against crashing. Higher "
                       "favours reliable drivers",
    "eliteMultiplierQualifying": "Divides the spread of qualifying times. "
                                 "Higher means faster times, closer together",
    "eliteMultiplierRace": "Divides the spread of race lap times. Higher means "
                           "faster laps, closer together",
    "homeBonusR": "Added to the reliability of drivers and teams racing at "
                  "home",
    "homeBonusA": "Added to the aggression of drivers and teams racing at home",
    "homeBonusT": "Added to the technique of drivers and teams racing at home",
}

WEIGHT_ROWS = (("ratingWeight", "RATing",
                "How much each contributes to a car's combined R, A and T"),
               ("rpWeight", "RP bonus",
                "How much each nation's RP bonus contributes to the car's"),
               ("experienceWeight", "Experience",
                "How much each contributes to combined experience. Zero "
                "everywhere means experience is ignored"))
WEIGHT_COLUMNS = ("Drivers", "Teams", "Tyres", "Engines")

# The widest grid a season allows, and so the longest the points table can get.
MAXIMUM_GRID = 30


def _headerMetrics():
    return QFontMetrics(QFont())


class XkorScorinatorParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.isFillingPoints = False

        # the points tab is built first: the grid size on the season tab drives
        # how many rows it has, so it has to exist before that spin box is wired
        self.tabs = QTabWidget()
        points = self._pointsTab()
        self.tabs.addTab(self._seasonTab(), "Season")
        self.tabs.addTab(self._modelTab(), "Model")
        self.tabs.addTab(points, "Points")

        layout = QGridLayout(self)
        layout.addWidget(self.tabs, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)

    # ------------------------------------------------------------------ helpers

    def setOption(self, key, value):
        self.options[key] = value
        self.optionsChanged.emit(self.options)

    def _addRow(self, form, label, key, widget):
        """A labelled row whose label and field share the setting's tooltip, so
        hovering either one explains it."""
        tip = TOOLTIPS.get(key, "")
        caption = QLabel(label)
        if tip:
            caption.setToolTip(tip)
            widget.setToolTip(tip)
        form.addRow(caption, widget)

    def _spin(self, key, minimum, maximum, step=1.0, decimals=2):
        box = QDoubleSpinBox()
        box.setDecimals(decimals)
        box.setRange(minimum, maximum)
        box.setSingleStep(step)
        box.setValue(toDouble(self.options.get(key, DEFAULTS[key])))
        box.valueChanged.connect(lambda v, k=key: self.setOption(k, v))
        return box

    def _intSpin(self, key, minimum, maximum):
        box = QSpinBox()
        box.setRange(minimum, maximum)
        box.setValue(toInt(self.options.get(key, DEFAULTS[key])))
        box.valueChanged.connect(lambda v, k=key: self.setOption(k, v))
        return box

    def _combo(self, key, choices):
        """XkorComboBox re-measures its popup on show, so the list can't come
        out narrower than its own items and clip them."""
        box = XkorComboBox()
        for label, value in choices:
            box.addItem(label, value)
        current = toString(self.options.get(key, DEFAULTS[key])).upper()[0:1]
        index = box.findData(current)
        box.setCurrentIndex(index if index >= 0 else 0)
        box.currentIndexChanged.connect(
            lambda i, k=key, b=box: self.setOption(k, toString(b.itemData(i))))
        return box

    def _yesNo(self, key):
        return self._combo(key, (("Yes", "Y"), ("No", "N")))

    # --------------------------------------------------------------------- tabs

    def _seasonTab(self):
        page = QWidget()
        form = QFormLayout(page)
        self._addRow(form, "Race distance (km):", "kmPerRace",
                     self._spin("kmPerRace", 1, 2000, 5, 0))
        self._addRow(form, "Car speed (% of lap record):", "speedPercent",
                     self._spin("speedPercent", 10, 300, 1, 1))
        grid = self._intSpin("driversOnGrid", 2, MAXIMUM_GRID)
        # a shorter grid means fewer positions to score
        grid.valueChanged.connect(lambda _v: self._fillPoints())
        self._addRow(form, "Drivers on grid:", "driversOnGrid", grid)
        self._addRow(form, "Safety car:", "safetyCar",
                     self._combo("safetyCar", (("Real", "R"), ("Virtual", "V"))))
        self._addRow(form, "Pole position bonus:", "polePositionBonus",
                     self._spin("polePositionBonus", 0, 25, 1, 1))
        self._addRow(form, "Fastest lap bonus:", "fastestLapBonus",
                     self._spin("fastestLapBonus", 0, 25, 1, 1))
        self._addRow(form, "Use tyre manufacturers:", "useTyres",
                     self._yesNo("useTyres"))
        self._addRow(form, "Use engine manufacturers:", "useEngines",
                     self._yesNo("useEngines"))
        self._addRow(form, "Show quarter-distance order:",
                     "showQuarterDistances",
                     self._yesNo("showQuarterDistances"))
        self._addRow(form, "Bi-national entities:", "alliances",
                     self._alliancesField())
        return page

    def _alliancesField(self):
        field = QLineEdit()
        field.setPlaceholderText("AAA+BBB, CCC+DDD")
        field.setText(", ".join(toString(i) for i in
                                toList(self.options.get("alliances", []))))
        field.editingFinished.connect(
            lambda f=field: self.setOption(
                "alliances", [i.strip() for i in f.text().split(",") if i.strip()]))
        return field

    def _modelTab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        dice = QFormLayout()
        self._addRow(dice, "Spin constant:", "spinConstant",
                     self._spin("spinConstant", 0, 90, 1, 1))
        self._addRow(dice, "Spin multiplier:", "spinMultiplier",
                     self._spin("spinMultiplier", 0, 10, 0.1))
        self._addRow(dice, "Crash constant:", "crashConstant",
                     self._spin("crashConstant", 0, 81, 1, 1))
        self._addRow(dice, "Crash multiplier:", "crashMultiplier",
                     self._spin("crashMultiplier", 0, 10, 0.1))
        self._addRow(dice, "Elite multiplier (qualifying):",
                     "eliteMultiplierQualifying",
                     self._spin("eliteMultiplierQualifying", 0.1, 20, 0.1))
        self._addRow(dice, "Elite multiplier (race):", "eliteMultiplierRace",
                     self._spin("eliteMultiplierRace", 0.1, 20, 0.1))
        self._addRow(dice, "Home bonus — R:", "homeBonusR",
                     self._spin("homeBonusR", 0, 10, 0.1))
        self._addRow(dice, "Home bonus — A:", "homeBonusA",
                     self._spin("homeBonusA", 0, 10, 0.1))
        self._addRow(dice, "Home bonus — T:", "homeBonusT",
                     self._spin("homeBonusT", 0, 10, 0.1))
        layout.addLayout(dice)

        caption = QLabel("Stat influence — how much each contributes")
        layout.addWidget(caption)
        layout.addWidget(self._weightsTable())
        return page

    def _weightsTable(self):
        table = QTableWidget(len(WEIGHT_ROWS), len(WEIGHT_COLUMNS))
        table.setHorizontalHeaderLabels(list(WEIGHT_COLUMNS))
        table.setVerticalHeaderLabels([r[1] for r in WEIGHT_ROWS])
        table.setGridStyle(Qt.NoPen)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setDefaultSectionSize(_headerMetrics().height() + 2)
        for row, (_prefix, _label, tip) in enumerate(WEIGHT_ROWS):
            table.verticalHeaderItem(row).setToolTip(tip)

        keys = {}
        for row, (prefix, _label, _tip) in enumerate(WEIGHT_ROWS):
            for column, name in enumerate(WEIGHT_COLUMNS):
                key = prefix + name
                keys[(row, column)] = key
                table.setItem(row, column, QTableWidgetItem(
                    toString(toDouble(self.options.get(key, DEFAULTS[key])))))

        table.cellChanged.connect(
            lambda row, column, t=table, k=keys: self.setOption(
                k[(row, column)], toDouble(t.item(row, column).text())))
        return table

    def _pointsTab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.pointsCaption = QLabel()
        layout.addWidget(self.pointsCaption)

        # everything the user has typed, kept at the widest grid the season
        # allows: shrinking the grid hides the tail rather than discarding it,
        # so nudging the spin box down and back up doesn't cost you the table
        values = toList(self.options.get("pointsPerPosition",
                                        defaultValue("pointsPerPosition")))
        self.pointsValues = [toDouble(values[row]) if row < len(values) else 0.0
                             for row in range(MAXIMUM_GRID)]

        self.pointsTable = QTableWidget(0, 1)
        self.pointsTable.setHorizontalHeaderLabels(["Points"])
        self.pointsTable.setGridStyle(Qt.NoPen)
        self.pointsTable.setAlternatingRowColors(True)
        self.pointsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pointsTable.verticalHeader().setDefaultSectionSize(
            _headerMetrics().height() + 2)
        self.pointsTable.cellChanged.connect(self._pointsEdited)

        self._fillPoints(store=False)
        layout.addWidget(self.pointsTable)
        return page

    def _gridSize(self):
        return max(1, min(toInt(self.options.get("driversOnGrid",
                                                DEFAULTS["driversOnGrid"])),
                          MAXIMUM_GRID))

    def _fillPoints(self, store=True):
        """Show one row per starter. Called on setup and whenever the grid size
        changes, so the table can't offer points for a position nobody can
        finish in — or hide one they can."""
        rows = self._gridSize()
        self.isFillingPoints = True
        try:
            self.pointsTable.setRowCount(rows)
            self.pointsTable.setVerticalHeaderLabels(
                [str(row + 1) for row in range(rows)])
            for row in range(rows):
                self.pointsTable.setItem(row, 0, QTableWidgetItem(
                    toString(self.pointsValues[row])))
        finally:
            self.isFillingPoints = False

        self.pointsCaption.setText(
            "Points awarded for each finishing position, one row per starter "
            "(%d on the grid)" % rows)
        if store:
            self.setOption("pointsPerPosition", self.pointsValues[:rows])

    def _pointsEdited(self, row, _column):
        if self.isFillingPoints:
            return  # our own repopulating, not the user typing
        item = self.pointsTable.item(row, 0)
        self.pointsValues[row] = toDouble(item.text()) if item is not None else 0.0
        self.setOption("pointsPerPosition",
                       self.pointsValues[:self.pointsTable.rowCount()])
