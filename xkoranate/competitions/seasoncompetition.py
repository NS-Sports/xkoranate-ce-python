"""A season of a racing series, as run by The Racing Scorinator.

The sheet's Input tab holds a calendar of circuits and its Standings tab
accumulates points, poles, wins and fastest laps across the season. Here the
calendar lives in the competition options (which is what decides how many
matchdays there are) and the standings are carried between matchdays through
resumeOpt, the same way XkorMultipleRunCompetition carries its attempt lists.

Each circuit contributes two matchdays — qualifying, then the race — except
circuits whose type is "Testing", which are practice-only and score nothing.
Qualifying sets the grid the race then starts from.
"""

from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.paradigms.scorinatorparadigm import DEFAULTS
from xkoranate.variant import toDouble, toInt, toList, toString

# Input!AJ:BA — the calendar columns, as parallel option lists. There is no
# event-name column: a race week is called "Grand Prix of" its host nation, the
# way the sheet's own calendar names them, so eventName() derives it.
CALENDAR_COLUMNS = ("circuitNations", "circuitNames",
                    "circuitTypes", "lapRecords", "trackLengths",
                    "aggressiveness", "technicality", "qualifyingFormats",
                    "rainChances", "overtakingDifficulties",
                    "errorPunishments")

# A new season starts with no calendar at all: the circuits are the whole point
# of the thing, and inventing a dozen of them for the user only means deleting
# them. Naming a circuit at the calendar step is what creates a race week.
DEFAULT_CALENDAR = {key: [] for key in CALENDAR_COLUMNS}

# What a race week gets when it is first named, so that typing a circuit and
# nothing else still produces a sane race rather than zero-second laps. These
# are also what a hand-edited calendar falls back to for anything left at zero.
NEW_WEEK = {
    "circuitTypes": "Race",
    "lapRecords": 60,
    "trackLengths": 4,
    "aggressiveness": 5,
    "technicality": 5,
    "qualifyingFormats": "Trad",
    "rainChances": 5,
    "overtakingDifficulties": 3,
    "errorPunishments": 3,
}

# The choices behind the calendar's two dropdown columns: what is stored, and
# what the user sees. The stored value is what the paradigm compares against.
CIRCUIT_TYPES = (("Race", "Race"), ("Testing", "Testing"))
QUALIFYING_FORMATS = (("Traditional", "Trad"), ("One shot", "OS"),
                      ("Two tier", "TT"), ("Elimination", "E"))
CHOICES = {"circuitTypes": CIRCUIT_TYPES,
           "qualifyingFormats": QUALIFYING_FORMATS}


def eventName(nation, stored=""):
    """What to call a race week: "Grand Prix of" the host nation. A single race
    can override it with a title of its own; a season calendar never does."""
    stored = toString(stored).strip()
    if stored:
        return stored
    nation = toString(nation).strip()
    return "Grand Prix of %s" % nation if nation else "Grand Prix"


def choiceLabel(key, value):
    """The label to show for a stored choice. Anything unrecognised is shown
    as typed, so a hand-edited file still reads back."""
    for label, stored in CHOICES.get(key, ()):
        if toString(value) == stored:
            return label
    return toString(value)


def weekValue(week, key):
    """A race week's number, falling back to the new-week default when it is
    zero or missing. A circuit with a zero-second lap record or zero length is
    not a circuit, so a half-filled row still races rather than dividing by
    nothing."""
    return toDouble(week.get(key)) or toDouble(NEW_WEEK[key])


def choiceValue(key, label):
    """The value to store for a shown label, accepting a stored code too."""
    label = toString(label).strip()
    for shown, stored in CHOICES.get(key, ()):
        if label == shown or label == stored:
            return stored
    return label


class _Standing:
    """One line of the drivers' championship."""

    def __init__(self, id="", name="", nation="", number="", tla="", team="",
                 tyres="", engine=""):
        self.id = id
        self.name = name
        self.nation = nation
        self.number = number
        self.tla = tla
        self.team = team
        self.tyres = tyres
        self.engine = engine
        self.points = 0.0
        self.poles = 0
        self.wins = 0
        self.fastestLaps = 0
        self.podiums = 0
        self.finishes = 0
        self.retirements = 0


class XkorSeasonCompetition(XkorAbstractCompetition):
    # everyone who signs up is in the field, so the groups step is free for the
    # calendar — which is the thing a season actually needs planning out
    def usesGroups(self):
        return False

    def plannerStepName(self):
        return "Calendar"

    def newPlannerWidget(self, options):
        from xkoranate.competitions.options.seasoncompetitionoptions import XkorSeasonCompetitionOptions

        return XkorSeasonCompetitionOptions(options)

    # ------------------------------------------------------------- the calendar

    def calendar(self):
        """The calendar as a list of dicts, one per race week."""
        columns = {}
        for key in CALENDAR_COLUMNS:
            columns[key] = toList(self.userOpt.get(key, DEFAULT_CALENDAR[key]))

        weeks = max(len(v) for v in columns.values()) if columns else 0
        rval = []
        for i in range(weeks):
            week = {}
            for key, values in columns.items():
                week[key] = values[i] if i < len(values) else ""
            if not toString(week["circuitNames"]):
                continue
            rval.append(week)
        return rval

    def _isTesting(self, week):
        return toString(week["circuitTypes"]).strip().lower().startswith("test")

    def _sessions(self):
        """The matchday list: (raceweek index, session name) pairs."""
        rval = []
        for index, week in enumerate(self.calendar()):
            if self._isTesting(week):
                rval.append((index, "practice"))
            else:
                rval.append((index, "qualifying"))
                rval.append((index, "race"))
        return rval

    def matchdays(self):
        return len(self._sessions())

    def matchdayNames(self):
        rval = []
        weeks = self.calendar()
        for index, session in self._sessions():
            label = {"practice": "Practice", "qualifying": "Qualifying",
                     "race": "Race"}[session]
            rval.append("Week %d: %s — %s" % (
                index + 1, label, toString(weeks[index]["circuitNames"])))
        return rval

    # ---------------------------------------------------------------- standings

    def _readStandings(self):
        """Pull the championship table back out of the options the previous
        matchday saved."""
        ids = [toString(i) for i in toList(self.userOpt.get("standingIDs", []))]
        points = toList(self.userOpt.get("standingPoints", []))
        poles = toList(self.userOpt.get("standingPoles", []))
        wins = toList(self.userOpt.get("standingWins", []))
        fastestLaps = toList(self.userOpt.get("standingFastestLaps", []))
        podiums = toList(self.userOpt.get("standingPodiums", []))
        finishes = toList(self.userOpt.get("standingFinishes", []))
        retirements = toList(self.userOpt.get("standingRetirements", []))

        rval = {}
        for i in range(len(ids)):
            s = _Standing(ids[i])
            s.points = toDouble(points[i]) if i < len(points) else 0.0
            s.poles = toInt(poles[i]) if i < len(poles) else 0
            s.wins = toInt(wins[i]) if i < len(wins) else 0
            s.fastestLaps = toInt(fastestLaps[i]) if i < len(fastestLaps) else 0
            s.podiums = toInt(podiums[i]) if i < len(podiums) else 0
            s.finishes = toInt(finishes[i]) if i < len(finishes) else 0
            s.retirements = toInt(retirements[i]) if i < len(retirements) else 0
            rval[s.id] = s
        return rval

    def _writeStandings(self, standings):
        order = list(standings.keys())
        self.resumeOpt["standingIDs"] = order
        self.resumeOpt["standingPoints"] = [standings[i].points for i in order]
        self.resumeOpt["standingPoles"] = [standings[i].poles for i in order]
        self.resumeOpt["standingWins"] = [standings[i].wins for i in order]
        self.resumeOpt["standingFastestLaps"] = [standings[i].fastestLaps for i in order]
        self.resumeOpt["standingPodiums"] = [standings[i].podiums for i in order]
        self.resumeOpt["standingFinishes"] = [standings[i].finishes for i in order]
        self.resumeOpt["standingRetirements"] = [standings[i].retirements for i in order]

    def _readHistory(self):
        """Per-matchday snapshots of the standings, so that reverting to an
        earlier matchday can restore them."""
        return toList(self.userOpt.get("matchdayHistory", []))

    def revertToMatchday(self, matchday):
        """Rewind the standings to the state they were in before `matchday`."""
        history = self._readHistory()
        self.resumeOpt = {}
        # carry the grid forward only if it was set before the cut
        grids = toList(self.userOpt.get("gridHistory", []))
        self.resumeOpt["matchdayHistory"] = [list(i) for i in history[:matchday]]
        self.resumeOpt["gridHistory"] = [list(i) for i in grids[:matchday]]

        if matchday > 0 and matchday - 1 < len(history):
            snapshot = toList(history[matchday - 1])
            self._restoreSnapshot(snapshot)
        else:
            for key in ("standingIDs", "standingPoints", "standingPoles",
                        "standingWins", "standingFastestLaps", "standingPodiums",
                        "standingFinishes", "standingRetirements"):
                self.resumeOpt[key] = []
            self.resumeOpt["startingGrid"] = []
        return dict(self.resumeOpt)

    def _restoreSnapshot(self, snapshot):
        keys = ("standingIDs", "standingPoints", "standingPoles", "standingWins",
                "standingFastestLaps", "standingPodiums", "standingFinishes",
                "standingRetirements")
        for index, key in enumerate(keys):
            self.resumeOpt[key] = toList(snapshot[index]) if index < len(snapshot) else []

    def _snapshot(self):
        return [list(toList(self.resumeOpt.get(key, [])))
                for key in ("standingIDs", "standingPoints", "standingPoles",
                            "standingWins", "standingFastestLaps",
                            "standingPodiums", "standingFinishes",
                            "standingRetirements")]

    # --------------------------------------------------------------- scorinate

    def scorinate(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        sessions = self._sessions()
        if matchday >= len(sessions):
            return
        weekIndex, session = sessions[matchday]
        week = self.calendar()[weekIndex]

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()
        localParadigmOptions["session"] = session
        localParadigmOptions["raceweek"] = weekIndex + 1
        localParadigmOptions["homeNation"] = toString(week["circuitNations"])
        localParadigmOptions["circuit"] = toString(week["circuitNames"])
        localParadigmOptions["lapRecord"] = weekValue(week, "lapRecords")
        localParadigmOptions["trackLength"] = weekValue(week, "trackLengths")
        localParadigmOptions["aggressiveness"] = weekValue(week, "aggressiveness")
        localParadigmOptions["technicality"] = weekValue(week, "technicality")
        localParadigmOptions["qualifyingFormat"] = toString(
            week["qualifyingFormats"]) or NEW_WEEK["qualifyingFormats"]
        # rain is the one setting whose zero means something, so it stands
        localParadigmOptions["rainChance"] = toDouble(week["rainChances"])
        localParadigmOptions["overtakingDifficulty"] = weekValue(
            week, "overtakingDifficulties")
        localParadigmOptions["errorPunishment"] = weekValue(week, "errorPunishments")
        if session == "race":
            localParadigmOptions["startingGrid"] = self._gridFor(matchday)

        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

        athletes = []
        for group in self.startList.groups:
            athletes.extend(group.athletes)

        p.scorinate(athletes)
        results = p.results()

        # resumeOpt only carries state; replaceCompetitionOptions() merges it
        # into the event's options, so the calendar survives untouched
        self.resumeOpt = {}
        standings = self._readStandings()
        self._identify(standings, results, athletes)

        if session == "race":
            self._recordRace(standings, results)

        self._writeStandings(standings)
        self._recordGrid(matchday, session, results)

        history = [list(toList(i)) for i in self._readHistory()]
        while len(history) <= matchday:
            history.append([])
        history[matchday] = self._snapshot()
        self.resumeOpt["matchdayHistory"] = history

        self.resultsBuf[matchday] = self._output(matchday, week, session, p,
                                                 results, standings)

    def _identify(self, standings, results, athletes):
        """Make sure every driver on the entry list has a standings line, and
        keep their team/tyre/engine details fresh."""
        byId = {toString(a.id): a for a in athletes}
        for id, athlete in byId.items():
            if id not in standings:
                standings[id] = _Standing(id)
        for r in results:
            id = toString(r.athlete.id)
            if id not in standings:
                standings[id] = _Standing(id)
            s = standings[id]
            s.name = r.athlete.name
            s.nation = r.athlete.nation
            s.number = toString(r.result.get("number"))
            s.tla = toString(r.result.get("tla"))
            s.team = toString(r.result.get("team"))
            s.tyres = toString(r.result.get("tyres"))
            s.engine = toString(r.result.get("engine"))

    def _recordRace(self, standings, results):
        polePoints = toDouble(self.paradigmOpt.get(
            "polePositionBonus", DEFAULTS["polePositionBonus"]))
        for r in results:
            s = standings[toString(r.athlete.id)]
            position = toInt(r.result.get("position"))
            s.points += toDouble(r.result.get("points"))
            if toInt(r.result.get("gridPosition")) == 1:
                s.poles += 1
                s.points += polePoints
            if position == 1:
                s.wins += 1
            if 1 <= position <= 3:
                s.podiums += 1
            if position >= 1:
                s.finishes += 1
            elif r.result.get("retiredOnLap"):
                s.retirements += 1
            if "fastestLap" in r.result:
                s.fastestLaps += 1

    def _recordGrid(self, matchday, session, results):
        """Qualifying writes the grid the next matchday's race reads."""
        grids = [list(toList(i)) for i in toList(self.userOpt.get("gridHistory", []))]
        while len(grids) <= matchday:
            grids.append([])
        if session == "qualifying":
            order = sorted((r for r in results
                            if toInt(r.result.get("gridPosition")) > 0),
                           key=lambda r: toInt(r.result.get("gridPosition")))
            grids[matchday] = [toString(r.athlete.id) for r in order]
        self.resumeOpt["gridHistory"] = grids

    def _gridFor(self, matchday):
        """The grid the previous matchday's qualifying produced."""
        grids = toList(self.userOpt.get("gridHistory", []))
        if matchday - 1 < len(grids):
            return [toString(i) for i in toList(grids[matchday - 1])]
        return []

    # ------------------------------------------------------------------ output

    def _output(self, matchday, week, session, paradigm, results, standings):
        title = self.matchdayNames()[matchday]
        rval = title + "\n" + "=" * len(title) + "\n"
        rval += "%s, %s\n\n" % (eventName(week["circuitNations"],
                                         week.get("circuitEvents", "")),
                               toString(week["circuitNations"]))
        rval += paradigm.output() + "\n"

        if session == "race":
            rval += self._quarterDistanceOutput(paradigm)
            rval += self._championshipOutput(standings)
        return rval

    def _quarterDistanceOutput(self, paradigm):
        if toString(self.paradigmOpt.get(
                "showQuarterDistances",
                DEFAULTS["showQuarterDistances"])).upper()[0:1] != "Y":
            return ""
        orders = getattr(paradigm, "quarterOrders", {})
        if not orders:
            return ""
        rval = "Running order\n"
        for lap in sorted(orders):
            names = ", ".join("%d %s" % (position, d.tla or d.athlete.name)
                              for position, d in enumerate(orders[lap], start=1))
            rval += "  After %d laps: %s\n" % (lap, names)
        return rval + "\n"

    def _championshipOutput(self, standings):
        nameWidth = self.nameWidth()
        lines = [s for s in standings.values() if s.name]
        lines.sort(key=lambda s: (-s.points, -s.wins, -s.podiums, s.name))

        rval = "Drivers' Championship\n"
        rval += "%-4s %-4s %s %s %6s %5s %5s %5s\n" % (
            "Pos", "#", "Driver".ljust(nameWidth), "Team".ljust(22),
            "Pts", "Wins", "Pole", "FL")
        for position, s in enumerate(lines, start=1):
            rval += "%-4d %-4s %s %s %6s %5s %5s %5s\n" % (
                position, s.number,
                self._formatAthleteNameFor(s).ljust(nameWidth)[:nameWidth],
                s.team.ljust(22)[:22],
                "%g" % s.points, s.wins or "", s.poles or "", s.fastestLaps or "")
        rval += "\n"

        teams = {}
        for s in lines:
            if not s.team:
                continue
            entry = teams.setdefault(s.team, {"points": 0.0, "wins": 0,
                                             "engine": s.engine, "tyres": s.tyres})
            entry["points"] += s.points
            entry["wins"] += s.wins
        if teams:
            rval += "Constructors' Championship\n"
            rval += "%-4s %s %s %6s %5s\n" % (
                "Pos", "Team".ljust(24), "Engine".ljust(22), "Pts", "Wins")
            order = sorted(teams.items(), key=lambda i: (-i[1]["points"], i[0]))
            for position, (name, entry) in enumerate(order, start=1):
                rval += "%-4d %s %s %6s %5s\n" % (
                    position, name.ljust(24)[:24],
                    toString(entry["engine"]).ljust(22)[:22],
                    "%g" % entry["points"], entry["wins"] or "")
            rval += "\n"
        return rval

    def _formatAthleteNameFor(self, standing):
        showTLAs = toString(self.paradigmOpt.get("showTLAs", "true")) == "true"
        if showTLAs and standing.nation:
            return "%s (%s)" % (standing.name, standing.nation)
        return standing.name
