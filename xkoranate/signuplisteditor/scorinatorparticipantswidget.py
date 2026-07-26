"""Participants for The Racing Scorinator: drivers and what they drive.

A racing series has four kinds of entrant — drivers, their teams, and the tyre
and engine manufacturers supplying them — and each has its own ratings. They
all belong in the participants step, so this widget stacks four participant
tables in tabs and stores every row in the one signup list, tagged with a
`kind` property. XkorScorinatorParadigm splits them apart again.

Drivers name their team by name and their tyres and engine by monogram (the
sheet's single-letter code), or by full name if that reads better.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ..variant import toString
from .athletewidget import XkorAthleteWidget

# key, header, type, tooltip ("" for a column that needs no explaining)
DRIVER_COLUMNS = (
    ("name", "Driver", "string", ""),
    ("nation", "NAT", "string", "The driver's nation, which its RP bonus and "
                                "any home-race bonus are keyed to"),
    ("skill", "Rank", "skill", "The driver's rank in the field, used for RP "
                               "bonus weighting"),
    ("number", "#", "string", "Car number, shown in results"),
    ("tla", "DRV", "string", "Three-letter driver code, shown in results and "
                             "in the running order"),
    ("team", "Team", "string", "Must match a team's name on the Teams tab"),
    ("tyres", "Tyres", "string", "Must match a monogram (or name) on the "
                                 "Tyres tab"),
    ("engines", "Engine", "string", "Must match a monogram (or name) on the "
                                    "Engines tab"),
    ("reliability", "R", "double", "Reliability — resists crashes and spins, "
                                   "and softens the cost of both"),
    ("aggression", "A", "double", "Aggression — pays off on circuits with a "
                                  "high aggressiveness rating"),
    ("technique", "T", "double", "Technique — pays off on circuits with a "
                                 "high technicality rating"),
    ("experience", "E", "double", "Experience — only has an effect if its "
                                  "stat-influence weight is above zero"),
)

TEAM_COLUMNS = (
    ("name", "Team", "string", "The name drivers refer to on the Drivers tab"),
    ("nation", "NAT", "string", "The team's nation, for RP and home-race "
                                "bonuses"),
    ("skill", "Rank", "skill", ""),
    ("reliability", "R", "double", "Reliability — how well the car holds "
                                   "together"),
    ("aggression", "A", "double", "Acceleration"),
    ("technique", "T", "double", "Turning"),
    ("experience", "E", "double", "Experience — only has an effect if its "
                                  "stat-influence weight is above zero"),
)

TYRE_COLUMNS = (
    ("name", "Manufacturer", "string", ""),
    ("nation", "NAT", "string", "The manufacturer's nation, for RP bonuses"),
    ("skill", "Rank", "skill", ""),
    ("monogram", "M", "string", "The single-letter code drivers use to pick "
                                "these tyres on the Drivers tab"),
    ("reliability", "R", "double", "Reliability — usually a small plus or "
                                   "minus, not a full rating"),
    ("technique", "T", "double", "Traction. Counts half towards both a "
                                 "driver's A and T"),
    ("experience", "E", "double", "Experience — only has an effect if its "
                                  "stat-influence weight is above zero"),
)

ENGINE_COLUMNS = (
    ("name", "Manufacturer", "string", ""),
    ("nation", "NAT", "string", "The manufacturer's nation, for RP bonuses"),
    ("skill", "Rank", "skill", ""),
    ("monogram", "M", "string", "The single-letter code drivers use to pick "
                                "this engine on the Drivers tab"),
    ("reliability", "R", "double", "Reliability — usually a small plus or "
                                   "minus, not a full rating"),
    ("aggression", "A", "double", "Actuation"),
    ("technique", "T", "double", "Tare"),
    ("experience", "E", "double", "Experience — only has an effect if its "
                                  "stat-influence weight is above zero"),
)

# kind tag, tab label, columns, whether the rank column is worth showing
KINDS = (
    ("driver", "Drivers", DRIVER_COLUMNS, True),
    ("team", "Teams", TEAM_COLUMNS, False),
    ("tyre", "Tyres", TYRE_COLUMNS, False),
    ("engine", "Engines", ENGINE_COLUMNS, False),
)

KIND_PROPERTY = "kind"


def _tab(columns, showRank):
    widget = XkorAthleteWidget([c[0] for c in columns], [c[1] for c in columns],
                               [c[2] for c in columns], -10, 10, 0.5)
    header = widget.treeWidget.headerItem()
    for index, (_key, _label, _type, tip) in enumerate(columns):
        if tip:
            header.setToolTip(index, tip)
    if not showRank:
        # only drivers are ranked; a team's rank would just be a puzzle
        widget.treeWidget.setColumnHidden([c[0] for c in columns].index("skill"),
                                          True)
    return widget


class XkorScorinatorParticipantsWidget(QWidget):
    """Quacks like XkorAthleteWidget, so XkorSignupListEditor can drive it."""

    listChanged = Signal()
    itemDeleted = Signal(object)  # QUuid
    signupListDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tabs = QTabWidget()
        self.widgets = {}
        for kind, label, columns, showRank in KINDS:
            widget = _tab(columns, showRank)
            widget.listChanged.connect(self.listChanged)
            widget.itemDeleted.connect(self.itemDeleted)
            widget.signupListDirectoryChanged.connect(self.signupListDirectoryChanged)
            self.widgets[kind] = widget
            self.tabs.addTab(widget, label)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.setContentsMargins(0, 0, 0, 0)

    def athletes(self):
        rval = []
        for kind, _label, _columns, _showRank in KINDS:
            for a in self.widgets[kind].athletes():
                # set the tag last: XkorAthleteWidget.athletes() rebuilds the
                # property dict from the visible columns
                a.setProperty(KIND_PROPERTY, kind)
                rval.append(a)
        return rval

    def setAthletes(self, athletes):
        for kind, _label, _columns, _showRank in KINDS:
            self.widgets[kind].setAthletes(
                [a for a in athletes if kindOf(a) == kind])

    def setMaxRank(self, newMax):
        for widget in self.widgets.values():
            widget.setMaxRank(newMax)

    def setMinRank(self, newMin):
        for widget in self.widgets.values():
            widget.setMinRank(newMin)


def kindOf(athlete):
    """An untagged entrant is a driver, so a signup list written by hand (or by
    an older version) still races."""
    kind = toString(athlete.property(KIND_PROPERTY))
    return kind if kind in (k[0] for k in KINDS) else "driver"
