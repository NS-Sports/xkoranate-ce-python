"""A single race weekend, as run by The Racing Scorinator.

The same engine as XkorSeasonCompetition, pointed at one circuit instead of a
calendar: qualifying sets the grid, the race is scored, and that is the end of
it. No championship tables, because there is no championship — points still
appear against each finisher so a one-off can be slotted into a series scored
somewhere else.
"""

from xkoranate.competitions.seasoncompetition import (CALENDAR_COLUMNS,
                                                     NEW_WEEK,
                                                     XkorSeasonCompetition)
from xkoranate.variant import toString

# The single-race options are the calendar's columns in the singular.
SINGLE_RACE_KEYS = {
    "circuitNations": "circuitNation",
    "circuitNames": "circuitName",
    "circuitTypes": None,  # a single race is always a race
    "lapRecords": "lapRecord",
    "trackLengths": "trackLength",
    "aggressiveness": "aggressiveness",
    "technicality": "technicality",
    "qualifyingFormats": "qualifyingFormat",
    "rainChances": "rainChance",
    "overtakingDifficulties": "overtakingDifficulty",
    "errorPunishments": "errorPunishment",
}

# One circuit still needs somewhere to start, so the neutral new-week values
# stand in; the circuit and its nation are the user's to name.
DEFAULT_CIRCUIT = {SINGLE_RACE_KEYS[key]: NEW_WEEK.get(key, "")
                   for key in CALENDAR_COLUMNS if SINGLE_RACE_KEYS[key]}
DEFAULT_CIRCUIT["rainChance"] = 5


class XkorSingleRaceCompetition(XkorSeasonCompetition):
    def plannerStepName(self):
        return "Circuit"

    def newPlannerWidget(self, options):
        from xkoranate.competitions.options.singleracecompetitionoptions import XkorSingleRaceCompetitionOptions

        return XkorSingleRaceCompetitionOptions(options)

    def calendar(self):
        """One race week, built from the scalar circuit options."""
        week = {}
        for key in CALENDAR_COLUMNS:
            singular = SINGLE_RACE_KEYS[key]
            if singular is None:
                week[key] = "Race"
            else:
                week[key] = self.userOpt.get(singular, DEFAULT_CIRCUIT[singular])
        # a one-off is where a title of its own makes sense, so unlike a season
        # calendar the single race keeps an optional event name
        week["circuitEvents"] = toString(self.userOpt.get("circuitEvent", ""))
        return [week]

    def _sessions(self):
        rval = []
        if toString(self.userOpt.get("includePractice", "N")).upper()[0:1] == "Y":
            rval.append((0, "practice"))
        rval.append((0, "qualifying"))
        rval.append((0, "race"))
        return rval

    def matchdayNames(self):
        circuit = toString(self.calendar()[0]["circuitNames"])
        labels = {"practice": "Practice", "qualifying": "Qualifying",
                  "race": "Race"}
        return ["%s — %s" % (labels[session], circuit)
                for _index, session in self._sessions()]

    def _championshipOutput(self, standings):
        return ""  # a one-off race has no championship to table
