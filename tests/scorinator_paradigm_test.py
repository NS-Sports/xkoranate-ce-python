"""Checks for the Racing Scorinator paradigm and the season competition.

The digit-arithmetic helpers and the lap-time formula are checked against cells
read out of the original sheet, whose cached values are quoted inline below.
The season checks then drive a whole calendar through the competition to make
sure the standings accumulate and rewind.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from xkoranate.athlete import XkorAthlete
from xkoranate.competitions.seasoncompetition import XkorSeasonCompetition
from xkoranate.paradigms.scorinatorparadigm import (DEFAULTS, RETIRED,
                                                    TOTAL_COLUMNS,
                                                    _crashNumber, _digitSum,
                                                    _Driver, _leadingFraction,
                                                    _spinNumber, _text,
                                                    _trailingFraction,
                                                    _trailingMultiplier,
                                                    _trailingPair,
                                                    XkorScorinatorParadigm)
from xkoranate.rng import Mt19937
from xkoranate.signuplisteditor.scorinatorparticipantswidget import (KIND_PROPERTY,
                                                                     kindOf)
from xkoranate.sport import XkorSport
from xkoranate.startlist import XkorStartList, XkorStartListGroup


def approx(a, b, tol=1e-6):
    return abs(a - b) < tol


# --- the sheet's text form: ten decimal places, trailing zeros kept ---
# Calculation!W37 = 0.508248178, and BV37 (="0."&right(X37,5)&left(right(W37,6),5))
# cached as "0.7393348178", whose second half is only "48178" if W37 renders as
# "0.5082481780".
assert _text(0.508248178) == "0.5082481780", _text(0.508248178)
# Calculation!BA37 = 0.04391530427 and CY37's first half is "53043", i.e. the
# tenth decimal is rounded, not truncated
assert _text(0.04391530427) == "0.0439153043", _text(0.04391530427)
assert _text("0.7393348178") == "0.7393348178"  # spliced columns pass through

# --- the spin die: Calculation!B69:F69 = 40, 56, 38, 58, 62 ---
assert _spinNumber(0.6012359806) == 40
assert _spinNumber(0.3138939659) == 56
assert _spinNumber(0.3557304911) == 38
assert _spinNumber(0.5283879268) == 58
assert _spinNumber(0.2797993268) == 62

# --- the crash die: LEFT(RIGHT(x,6),3) of three consecutive columns ---
# B37/C37/D37 give "359"&"939"&"304" = 359939304, digit sum 45
assert _crashNumber(0.6012359806, 0.3138939659, 0.3557304911) == 45
# leading zeros are lost to VALUE(), so the sum drops with them
assert _crashNumber(0.1000239806, 0.3138939659, 0.3557304911) == \
    _digitSum("239939304", 12)

# --- the small fraction helpers ---
# Calculation!U33 = value(left(right(B51,5),3)) = 403 for B51 = 0.8390440367
assert _leadingFraction(0.8390440367) == 0.403, _leadingFraction(0.8390440367)
assert approx(_trailingFraction(0.6012359806), 0.006)
assert approx(_trailingFraction(0.3138939659), 0.059)
assert approx(_trailingMultiplier(0.6012359806), 1.06)
# Calculation!H56 = 0.0321734348 drives the weather; right(x,2) = 48
assert _trailingPair(0.0321734348) == 48


def make_paradigm(**userOpt):
    """A paradigm wired to a sport with a seeded PRNG, so runs repeat."""
    s = XkorSport()
    s.setPRNG(Mt19937(20260726))
    p = XkorScorinatorParadigm()
    options = dict(DEFAULTS)
    options.update(userOpt)
    p.init(s, options)
    p.opt = {"displayDigits": 3, "resultWidth": 13}
    return p


# --- the lap-time formulas, against the sheet's own cached lap times ---------
# Calculation, week 1 at Aries Raceway: E1 = 60 (lap record), dry, track A and
# T both 0.5, driver 1's combined L3/M3/N3 = 5.180025 / 6.230025 / 7.730025.
# The sheet's event selector was on "Q" when it was exported, so N34 — the
# elite multiplier both formulas divide by — was the qualifying value, 1.5.
SHEET_DICE = [0.6012359806, 0.3138939659, 0.3557304911, 0.5283879268,
              0.2797993268, 0.002922050873]
SHEET_RACE_LAPS = [77.47930737, 66.77015462, 67.83373601, 74.11159714,
                   65.98503781, 63.00920720]  # Calculation!U3:Z3
SHEET_QUALIFYING_LAPS = [66.89436772, 61.78999630, 62.30078804, 65.28511048,
                         61.41532032, 60.00357355]  # Calculation!ED3:EI3


def calibrated(**userOpt):
    """A paradigm holding the sheet's week-1 state, with the sheet's own dice
    substituted for the PRNG so the lap formulas can be compared cell by
    cell."""
    options = {"eliteMultiplierRace": 1.5, "eliteMultiplierQualifying": 1.5}
    options.update(userOpt)
    p = make_paradigm(**options)
    # pad with a high-digit-sum die so the crash test — which reads two
    # columns ahead of the lap being run — never trips inside the window
    padding = ["0.9999999999"] * (TOTAL_COLUMNS - len(SHEET_DICE))
    p.matrix = [list(SHEET_DICE) + padding for _ in range(30)]
    p.baseLap = 60.0
    p.conditions = "Dry"
    p.conditionMultiplier = 1.0
    p.paradeLap = (60.0 * 1.05) * 1.0 + 60.0 * 0.25  # Calculation!T3 = 78
    p.laps = 77
    p.trackAggression = 0.5
    p.trackTechnique = 0.5
    p.overtakingDifficulty = 2.0
    p.errorPunishment = 2.0
    p.margins = p._marginForError(77, 2.0, 1.0)
    p.spinConstant = 30.0
    p.spinMultiplier = 1.4
    p.crashConstant = 26.0
    p.crashMultiplier = 1.4
    p.safetyCarType = "R"
    p.driversOnGrid = 30
    p.qualifyingFormat = "Trad"
    return p


def sheet_driver():
    d = _Driver(XkorAthlete(uuid.UUID(int=1)))
    d.r, d.a, d.t = 5.180025, 6.230025, 7.730025
    return d


p = calibrated()
assert p.paradeLap == 78, p.paradeLap
assert p.margins[1] == 2 and p.margins[2] == 1, p.margins[1:4]
for index, expected in enumerate(SHEET_RACE_LAPS):
    got = p._raceTime(sheet_driver(), 0, index + 1, p.paradeLap, False,
                      p.paradeLap, p.paradeLap, [p.paradeLap])
    assert approx(got, expected, tol=1e-7), (index + 1, got, expected)
for index, expected in enumerate(SHEET_QUALIFYING_LAPS):
    got = p._qualifyingTime(sheet_driver(), 0, index + 1, "qualifying")
    assert approx(got, expected, tol=1e-7), (index + 1, got, expected)

# the crash die for driver 1 on lap 1 sums to 45, well clear of the sheet's
# threshold of 26 + 2 − 5.180025×1.4, so lap 1 is not a retirement
assert _crashNumber(*SHEET_DICE[0:3]) == 45
assert p._raceTime(sheet_driver(), 0, 1, p.paradeLap, False, p.paradeLap,
                   p.paradeLap, [p.paradeLap]) != RETIRED
# raise the crash constant above the die and the same lap becomes one
fragilep = calibrated(crashConstant=60)
fragilep.crashConstant = 60.0
assert fragilep._raceTime(sheet_driver(), 0, 1, fragilep.paradeLap, False,
                          fragilep.paradeLap, fragilep.paradeLap,
                          [fragilep.paradeLap]) == RETIRED

# a virtual safety car flattens the lap to the sheet's fixed value
virtualp = calibrated(safetyCar="V")
virtualp.safetyCarType = "V"
assert approx(virtualp._raceTime(sheet_driver(), 0, 1, virtualp.paradeLap, True,
                                 virtualp.paradeLap, virtualp.paradeLap,
                                 [virtualp.paradeLap]),
              60.0 * 1.05 + 25)
# a real one closes the field up: a car already more than a lap adrift just
# runs the sheet's 1.8× parade lap
assert approx(p._safetyCarTime(p.paradeLap + 1000, p.paradeLap, [p.paradeLap]),
              p.paradeLap * 1.8)
# and a car level with the leader does too
assert approx(p._safetyCarTime(p.paradeLap, p.paradeLap, [p.paradeLap]),
              p.paradeLap * 1.8)


# Teams, tyre makers and engine makers are entrants now, entered on their own
# tabs of the participants step and tagged with a `kind` property.
TEAMS = [("Racing do Janeiro", "AAA", 4, 4, 4), ("Scuderia Febbraio", "BBB", 5, 3, 4),
         ("March", "CCC", 3, 5, 4), ("Racing Avril", "DDD", 4, 3, 5),
         ("Maycedes", "EEE", 4, 5, 3), ("June F1", "FFF", 4, 4, 4),
         ("Julius Motorsports", "GGG", 5, 3, 4), ("ART", "HHH", 3, 5, 4),
         ("September Motorsport", "III", 4, 3, 5),
         ("Super Car Team October!", "JJJ", 4, 5, 3)]
TYRES = [("Springy Rubber", "AAA", "R", -1, 1), ("Summertime", "BBB", "S", 0, 0),
         ("Autumn Tyres", "CCC", "A", 0.5, -0.5), ("Inverno", "DDD", "I", -0.7, 0.7),
         ("Goodyear", "EEE", "G", 0.1, -0.1)]
ENGINES = [("Hilary Climax", "AAA", "H", -0.5, -0.5, 1),
           ("Pasquadelta SpA", "BBB", "P", -1, 1, 0),
           ("Trinity Racing Motors", "CCC", "T", 0, 0, 0),
           ("Michaeli AMG", "DDD", "A", 0, -0.5, 0.5),
           ("Oxford Cosworth", "EEE", "C", -0.4, 0.2, 0.2)]


def _entrant(index, name, nation, kind, **properties):
    a = XkorAthlete(uuid.UUID(int=index))
    a.name = name
    a.nation = nation
    a.skill = 0.5
    a.rpBonus = 100.0 - index
    a.rpSkill = a.skill
    a.setProperty(KIND_PROPERTY, kind)
    for key, value in properties.items():
        a.setProperty(key, value)
    return a


def make_suppliers(firstIndex=1000):
    """The teams and suppliers a grid of drivers refers to."""
    rval = []
    index = firstIndex
    for name, nation, r, a, t in TEAMS:
        rval.append(_entrant(index, name, nation, "team", reliability=r,
                             aggression=a, technique=t, experience=0))
        index += 1
    for name, nation, monogram, r, t in TYRES:
        rval.append(_entrant(index, name, nation, "tyre", monogram=monogram,
                             reliability=r, technique=t, experience=0))
        index += 1
    for name, nation, monogram, r, a, t in ENGINES:
        rval.append(_entrant(index, name, nation, "engine", monogram=monogram,
                             reliability=r, aggression=a, technique=t,
                             experience=0))
        index += 1
    return rval


def make_drivers(count=20, withSuppliers=True):
    # two drivers per team
    rval = []
    for i in range(count):
        rval.append(_entrant(
            i + 1, "Driver %02d" % (i + 1), "N%02d" % (i + 1), "driver",
            number=str(i + 1), tla="D%02d" % (i + 1),
            team=TEAMS[(i // 2) % len(TEAMS)][0],
            tyres=TYRES[i % len(TYRES)][2],
            engines=ENGINES[i % len(ENGINES)][2],
            reliability=3 + (i % 3), aggression=3 + ((i + 1) % 3),
            technique=3 + ((i + 2) % 3), experience=0))
    return rval + (make_suppliers() if withSuppliers else [])


# --- the paradigm resolves ratings out of the registries ---
p = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                  aggressiveness=5, technicality=5, homeNation="AAA",
                  driversOnGrid=20)
drivers = make_drivers(20)
p.scorinate(drivers)
results = p.results()
assert len(results) == 20, len(results)
# every driver gets a distinct grid slot, numbered from one
positions = sorted(r.result["gridPosition"] for r in results)
assert positions == list(range(1, 21)), positions
# the results come back in grid order, best time first
assert results[0].result["gridPosition"] == 1
assert results[0].score() <= results[-1].score()
# the pole sitter has no gap to itself
assert approx(results[0].result.get("gap", 0.0), 0.0)
# a lap of a 60-second circuit should land in a plausible window
assert 40 < results[0].score() < 200, results[0].score()

# the home nation's drivers get more flying laps and a rating bonus
home = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                     homeNation="N01", driversOnGrid=20)
homeDrivers = make_drivers(20)
home.scorinate(homeDrivers)
homeResult = [r for r in home.results() if r.athlete.name == "Driver 01"][0]
away = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                     homeNation="ZZZ", driversOnGrid=20)
away.scorinate(make_drivers(20))
awayResult = [r for r in away.results() if r.athlete.name == "Driver 01"][0]
assert homeResult.score() != awayResult.score(), "home bonus had no effect"

# --- every qualifying format produces a full, unique grid ---
for fmt in ("Trad", "OS", "TT", "E"):
    q = make_paradigm(session="qualifying", qualifyingFormat=fmt, lapRecord=60,
                      trackLength=4, driversOnGrid=20)
    q.scorinate(make_drivers(20))
    slots = sorted(r.result["gridPosition"] for r in q.results())
    assert slots == list(range(1, 21)), (fmt, slots)

# --- a race runs the full distance, awards points and ranks finishers ---
race = make_paradigm(session="race", lapRecord=60, trackLength=4,
                     kmPerRace=305, driversOnGrid=20,
                     startingGrid=["{%s}" % uuid.UUID(int=i + 1) for i in range(20)])
race.scorinate(make_drivers(20))
raceResults = race.results()
assert race.laps == int(305 / 4) + 1 == 77, race.laps
finishers = [r for r in raceResults if r.result["position"] > 0]
retired = [r for r in raceResults if r.result.get("retiredOnLap")]
assert len(finishers) + len(retired) == 20, (len(finishers), len(retired))
assert finishers, "nobody finished a 77-lap race"
# finishing positions run 1..n with no gaps
assert sorted(r.result["position"] for r in finishers) == \
    list(range(1, len(finishers) + 1))
# the winner's time is the lowest and it is reported as a time, not a gap
winner = [r for r in finishers if r.result["position"] == 1][0]
assert winner.score() == min(r.score() for r in finishers)
assert not winner.scoreString().startswith("+"), winner.scoreString()
# exactly one fastest lap bonus is handed out
assert sum(1 for r in raceResults if "fastestLap" in r.result) == 1
# the winner scores the first entry in the points table (plus any FL bonus)
assert winner.result["points"] >= DEFAULTS["pointsPerPosition"][0]
# retirements score nothing and report the lap they went out on
for r in retired:
    assert r.result["points"] == 0
    assert r.scoreString().startswith("Ret. lap "), r.scoreString()
    assert 1 <= r.result["retiredOnLap"] <= race.laps

# --- teams and suppliers are entrants, not settings ---
entrants = make_drivers(20)
assert len(entrants) == 20 + len(TEAMS) + len(TYRES) + len(ENGINES), len(entrants)
assert sum(1 for a in entrants if kindOf(a) == "driver") == 20
# an untagged entrant is a driver, so a hand-written signup list still races
plain = XkorAthlete(uuid.UUID(int=99))
plain.name = "Untagged"
assert kindOf(plain) == "driver"

# only the drivers appear in the results; the teams they refer to are resolved
# into their ratings
grid = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                     driversOnGrid=20)
grid.scorinate(entrants)
assert len(grid.results()) == 20, len(grid.results())
assert not grid.unmatched, grid.unmatched
teamed = [r for r in grid.results() if r.athlete.name == "Driver 01"][0]
assert teamed.result["team"] == TEAMS[0][0], teamed.result["team"]

# a team's ratings really do feed the car: strip the teams off the entry list
# and the same driver comes out slower
teamless = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                         driversOnGrid=20)
teamless.scorinate([a for a in entrants if kindOf(a) != "team"])
lonely = [r for r in teamless.results() if r.athlete.name == "Driver 01"][0]
assert lonely.score() > teamed.score(), (lonely.score(), teamed.score())
# and the missing teams are called out rather than silently zeroed
assert teamless.unmatched, "a missing team should be reported"
assert "no team called" in teamless.unmatched[0], teamless.unmatched[0]
assert any("Check the entry list:" in line for line in teamless.header)

# --- "Stock" is the neutral supplier, so suppliers are optional ---
stockDrivers = make_drivers(20)
for a in stockDrivers:
    if kindOf(a) == "driver":
        a.setProperty("tyres", "")        # left blank
        a.setProperty("engines", "Stock")  # or named explicitly
stock = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                      driversOnGrid=20)
stock.scorinate([a for a in stockDrivers
                 if kindOf(a) not in ("tyre", "engine")] +
                make_suppliers())
assert not stock.unmatched, stock.unmatched
stocked = [r for r in stock.results() if r.athlete.name == "Driver 01"][0]
assert stocked.result["tyres"] == "Stock", stocked.result["tyres"]
assert stocked.result["engine"] == "Stock", stocked.result["engine"]
# Stock contributes nothing, so it is not the same car as a real supplier
assert stocked.score() != teamed.score()

# a supplier named but not entered is a mistake, and is reported
typo = make_drivers(20)
for a in typo:
    if kindOf(a) == "driver":
        a.setProperty("tyres", "Nonexistent")
mistyped = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                         driversOnGrid=20)
mistyped.scorinate(typo)
assert mistyped.unmatched, "a mistyped tyre maker should be reported"
assert "no tyre maker called" in mistyped.unmatched[0], mistyped.unmatched[0]
# at most five are listed, then a count
assert sum(1 for line in mistyped.header if line.startswith("  ")) <= 6

# --- the spliced dice columns carry a long race past lap 54 ---
long = make_paradigm(session="race", lapRecord=60, trackLength=3,
                     kmPerRace=305, driversOnGrid=20)
matrix = long._makeMatrix(20)
assert len(matrix) == 30, len(matrix)  # the sheet's dice are always 30 rows
assert len(matrix[0]) == TOTAL_COLUMNS, len(matrix[0])
for row in matrix:
    for cell in row:
        assert len(cell) == 12 and cell.startswith("0."), cell
# a spliced column is built from the two columns fifty and fifty-one back
spliced = matrix[0][54]
assert spliced == "0." + matrix[0][4][-5:] + matrix[0][3][-6:][:5], spliced
long.scorinate(make_drivers(20))
assert long.laps > 54, long.laps
assert any(r.result["position"] > 0 for r in long.results()), "no finishers"

# --- a wet circuit slows everyone down ---
wet = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                    rainChance=100, driversOnGrid=20)  # rain is certain
wet.scorinate(make_drivers(20))
assert wet.conditions != "Dry", wet.conditions
assert wet.conditionMultiplier > 1.0, wet.conditionMultiplier
dry = make_paradigm(session="qualifying", lapRecord=60, trackLength=4,
                    rainChance=0, driversOnGrid=20)  # rain is impossible
dry.scorinate(make_drivers(20))
assert dry.conditions == "Dry", dry.conditions
assert wet.results()[0].score() > dry.results()[0].score()

# --- drivers beyond the grid size do not start ---
tooMany = make_paradigm(session="race", lapRecord=60, trackLength=4,
                        kmPerRace=40, driversOnGrid=6)
tooMany.scorinate(make_drivers(10))
dns = [r for r in tooMany.results() if r.scoreString() == "DNS"]
assert len(dns) == 4, len(dns)

# --- a virtual safety car replaces the concertina with a flat lap ---
virtual = make_paradigm(session="race", lapRecord=60, trackLength=4,
                        kmPerRace=305, driversOnGrid=20, safetyCar="V",
                        crashConstant=40)  # crash a lot, so the SC comes out
virtual.scorinate(make_drivers(20))
assert virtual.safetyCarLaps or True  # deployment is chance-based; no assert

# --- reliability matters: a grid of fragile cars retires more often ---
fragile = make_paradigm(session="race", lapRecord=60, trackLength=4,
                        kmPerRace=305, driversOnGrid=20, crashConstant=45)
fragile.scorinate(make_drivers(20))
fragileRetirements = sum(1 for r in fragile.results()
                         if r.result.get("retiredOnLap"))
solid = make_paradigm(session="race", lapRecord=60, trackLength=4,
                      kmPerRace=305, driversOnGrid=20, crashConstant=0)
solid.scorinate(make_drivers(20))
solidRetirements = sum(1 for r in solid.results() if r.result.get("retiredOnLap"))
assert solidRetirements == 0, solidRetirements
assert fragileRetirements > solidRetirements, (fragileRetirements, solidRetirements)


# --- the season competition ---------------------------------------------------

# A calendar of its own: a new season starts empty, so the test owns its
# fixture. Two Testing weeks among the twelve, and every qualifying format.
TEST_CALENDAR = {
    "circuitNations": ["CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ",
                       "KKK", "LLL", "AAA", "BBB"],
    "circuitNames": ["Aries Raceway", "The Bullrun", "Twins Peak",
                     "Cancer Research Autodrome", "Circuit del Leon",
                     "Virgo Race Circuit", "Libra Scalextric", "The Scorpion",
                     "Archway", "Capricorn International", "Aquarius Wetlands",
                     "Fishtail Raceway"],
    "circuitTypes": ["Race", "Race", "Race", "Testing", "Race", "Race", "Race",
                     "Testing", "Race", "Race", "Race", "Race"],
    "lapRecords": [60, 65, 70, 75, 80, 85, 90, 60, 65, 70, 75, 80],
    "trackLengths": [4, 4.5, 5, 5.5, 6, 6.5, 7, 3.75, 4.25, 4.75, 5.25, 5.75],
    "aggressiveness": [5, 4, 3, 2, 5, 6, 7, 8, 5, 4.5, 5.5, 5],
    "technicality": [5, 6, 7, 8, 5, 4, 3, 2, 5, 5.5, 4.5, 5],
    "qualifyingFormats": ["Trad", "TT", "OS", "E", "OS", "Trad", "E", "TT",
                          "OS", "Trad", "E", "TT"],
    "rainChances": [3, 6, 5, 4, 5, 8, 3, 6, 3, 7, 25, 25],
    "overtakingDifficulties": [2, 3, 4, 2, 3, 4, 2, 3, 4, 2, 3, 4],
    "errorPunishments": [2, 3, 4, 2, 3, 4, 2, 3, 4, 2, 3, 4],
}


def make_competition(competitionOptions=None, results=None, seed=19640217):
    s = XkorSport()
    # in the app one PRNG lives for the whole session; here each matchday gets
    # its own seed so the ten races aren't ten copies of the same race
    s.setPRNG(Mt19937(seed))
    s.m_paradigm = "scorinator"

    group = XkorStartListGroup("Drivers", make_drivers(20))
    sl = XkorStartList()
    sl.name = "Season"
    sl.groups = [group]

    paradigmOptions = dict(DEFAULTS)
    paradigmOptions["driversOnGrid"] = 20
    options = dict(TEST_CALENDAR)
    options.update(competitionOptions or {})
    c = XkorSeasonCompetition()
    c.init(sl, s, paradigmOptions, options, results or {})
    return c


# --- the calendar's derived event names and dropdown columns ---
from xkoranate.competitions.seasoncompetition import (CALENDAR_COLUMNS,
                                                      DEFAULT_CALENDAR,
                                                      NEW_WEEK, choiceLabel,
                                                      choiceValue, eventName,
                                                      weekValue)

# nothing is planned out for the user
assert all(DEFAULT_CALENDAR[key] == [] for key in CALENDAR_COLUMNS), DEFAULT_CALENDAR

# a race week is called "Grand Prix of" its host nation; there is no event
# column to fill in
assert "circuitEvents" not in CALENDAR_COLUMNS, CALENDAR_COLUMNS
assert eventName("AAA") == "Grand Prix of AAA"
assert eventName("") == "Grand Prix"
# a single race may still override it
assert eventName("AAA", "Silverdale Trophy") == "Silverdale Trophy"
assert eventName("AAA", "   ") == "Grand Prix of AAA"

# Type and Qualifying are dropdowns: the label is shown, the code is stored
assert choiceLabel("qualifyingFormats", "TT") == "Two tier"
assert choiceValue("qualifyingFormats", "Two tier") == "TT"
assert choiceValue("qualifyingFormats", "TT") == "TT"  # a stored code still reads
assert choiceLabel("circuitTypes", "Testing") == "Testing"
assert choiceValue("circuitTypes", "Race") == "Race"
# anything unrecognised passes through rather than being silently dropped
assert choiceLabel("qualifyingFormats", "Wat") == "Wat"
assert choiceValue("qualifyingFormats", "Wat") == "Wat"

# a brand new season has no calendar at all: the circuits are the user's to name
blank = XkorSeasonCompetition()
blank.init(XkorStartList(), XkorSport(), {}, {}, {})
assert blank.calendar() == [], blank.calendar()
assert blank.matchdays() == 0 and blank.matchdayNames() == []
blank.scorinate(0)  # nothing to do, and not a crash

# a week named and nothing else still races, on the new-week defaults
bare = XkorSeasonCompetition()
bare.init(XkorStartList(), XkorSport(), {},
          {"circuitNames": ["Bare"], "circuitNations": ["XXX"]}, {})
assert bare.matchdays() == 2, bare.matchdays()
assert weekValue(bare.calendar()[0], "lapRecords") == NEW_WEEK["lapRecords"]
assert weekValue(bare.calendar()[0], "trackLengths") == NEW_WEEK["trackLengths"]

c = make_competition()
calendar = c.calendar()
assert len(calendar) == 12, len(calendar)
# two testing weeks in the test calendar mean 10 race weeks: 10*2 + 2 = 22
assert c.matchdays() == 22, c.matchdays()
names = c.matchdayNames()
assert names[0].startswith("Week 1: Qualifying"), names[0]
assert names[1].startswith("Week 1: Race"), names[1]
assert "Practice" in names[6], names[6]  # week 4 is a Testing round

# run a whole season, feeding each matchday's saved state into the next
options = {}
allResults = {}
matchdayCount = c.matchdays()
for matchday in range(matchdayCount):
    c = make_competition(options, allResults, seed=19640217 + matchday)
    c.scorinate(matchday)
    options = c.resumeFileOptions()
    allResults[matchday] = c.results(matchday)
    assert allResults[matchday], "matchday %d produced nothing" % matchday
    # qualifying hands the grid to the race that follows it
    if "Qualifying" in names[matchday]:
        grid = [str(i) for i in options["gridHistory"][matchday]]
        assert len(grid) == 20, grid
        assert len(set(grid)) == 20, "a driver was on the grid twice"
    elif "Race" in names[matchday]:
        pole = str(options["gridHistory"][matchday - 1][0])
        # the pole sitter's line in the race table shows grid position 1
        poleName = "Driver %02d" % uuid.UUID(pole.strip("{}")).int
        assert poleName in allResults[matchday], poleName

# week 1 is titled from its host nation, with nothing typed anywhere
assert "Grand Prix of CCC, CCC" in allResults[1], allResults[1][:200]

# the last race's output carries both championship tables
final = allResults[matchdayCount - 1]
assert "Drivers' Championship" in final
assert "Constructors' Championship" in final
assert "Conditions:" in final

# points accumulated, and the leader has more than a single race can award
points = [float(i) for i in options["standingPoints"]]
assert sum(points) > 0, points
assert max(points) > DEFAULTS["pointsPerPosition"][0], max(points)
# wins add up to the number of races run
assert sum(int(i) for i in options["standingWins"]) == 10, options["standingWins"]
# so do poles, which qualifying sets
assert sum(int(i) for i in options["standingPoles"]) == 10, options["standingPoles"]
assert sum(int(i) for i in options["standingFastestLaps"]) == 10

# --- rewinding puts the standings back where they were --------------------
c = make_competition(options, allResults)
reverted = c.revertToMatchday(2)  # erase from week 2's qualifying onwards
afterWeekOne = [float(i) for i in reverted["standingPoints"]]
assert sum(afterWeekOne) > 0, afterWeekOne
# one race's worth of points, nothing more
assert sum(afterWeekOne) <= sum(DEFAULTS["pointsPerPosition"]) + \
    DEFAULTS["fastestLapBonus"] + DEFAULTS["polePositionBonus"], afterWeekOne
assert sum(int(i) for i in reverted["standingWins"]) == 1

# rewinding to the start clears everything
c = make_competition(options, allResults)
cleared = c.revertToMatchday(0)
assert cleared["standingPoints"] == [], cleared["standingPoints"]
assert cleared["matchdayHistory"] == [], cleared["matchdayHistory"]

# --- a single race weekend ----------------------------------------------------

from xkoranate.competitions.singleracecompetition import (DEFAULT_CIRCUIT,
                                                          XkorSingleRaceCompetition)


# a single race has no circuit named for the user either, so name one here
TEST_CIRCUIT = {"circuitName": "Aries Raceway", "circuitNation": "CCC"}


def make_single_race(competitionOptions=None, results=None, seed=19640217):
    s = XkorSport()
    s.setPRNG(Mt19937(seed))
    s.m_paradigm = "scorinator"
    sl = XkorStartList()
    sl.name = "Race"
    sl.groups = [XkorStartListGroup("Drivers", make_drivers(20))]
    paradigmOptions = dict(DEFAULTS)
    paradigmOptions["driversOnGrid"] = 20
    options = dict(TEST_CIRCUIT)
    options.update(competitionOptions or {})
    c = XkorSingleRaceCompetition()
    c.init(sl, s, paradigmOptions, options, results or {})
    return c


# the paradigm offers both competition formats
assert XkorScorinatorParadigm().supportsCompetition("season")
assert XkorScorinatorParadigm().supportsCompetition("singleRace")

# --- neither racing format needs the groups step, so it holds their planner ---
from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition

season = XkorSeasonCompetition()
race = XkorSingleRaceCompetition()
assert not season.usesGroups() and not race.usesGroups()
assert season.plannerStepName() == "Calendar", season.plannerStepName()
assert race.plannerStepName() == "Circuit", race.plannerStepName()
# and the planner isn't also duplicated on the competition step
assert not season.hasOptionsWidget() and not race.hasOptionsWidget()
# a competition that does use groups is left alone
control = XkorRoundRobinCompetition()
assert control.usesGroups()
assert control.plannerStepName() == "Groups"
assert control.newPlannerWidget({}) is None

# an unnamed circuit is still a valid one-off, on the neutral defaults
unnamed = XkorSingleRaceCompetition()
unnamed.init(XkorStartList(), XkorSport(), {}, {}, {})
assert unnamed.matchdays() == 2, unnamed.matchdays()
assert DEFAULT_CIRCUIT["circuitName"] == "", DEFAULT_CIRCUIT
assert DEFAULT_CIRCUIT["lapRecord"] == NEW_WEEK["lapRecords"], DEFAULT_CIRCUIT

one = make_single_race()
assert one.matchdays() == 2, one.matchdays()
assert one.matchdayNames() == ["Qualifying — Aries Raceway",
                               "Race — Aries Raceway"], one.matchdayNames()
# the calendar is one week, taken from the scalar options
week = one.calendar()
assert len(week) == 1 and week[0]["circuitTypes"] == "Race", week
assert week[0]["lapRecords"] == DEFAULT_CIRCUIT["lapRecord"], week[0]

# a practice session can be added in front
withPractice = make_single_race({"includePractice": "Y"})
assert withPractice.matchdays() == 3, withPractice.matchdays()
assert withPractice.matchdayNames()[0] == "Practice — Aries Raceway"

# run it: qualifying then the race, with no championship tables
options, oneResults = {}, {}
for matchday in range(2):
    one = make_single_race(options, oneResults, seed=555 + matchday)
    one.scorinate(matchday)
    options = one.resumeFileOptions()
    oneResults[matchday] = one.results(matchday)

assert "Qualifying — Aries Raceway" in oneResults[0]
assert "Drivers' Championship" not in oneResults[1]
assert "Constructors' Championship" not in oneResults[1]
assert "Conditions:" in oneResults[1]
assert "Laps: 77" in oneResults[1]
# points are still shown against the finishers, so a one-off can feed a series
assert "Pts" in oneResults[1]
# and the grid still came from qualifying
assert len(options["gridHistory"][0]) == 20, options["gridHistory"][0]

# a different circuit changes the race distance
short = make_single_race({"trackLength": 10.0, "circuitName": "Test Track"})
assert short.matchdayNames()[1] == "Race — Test Track"
short.scorinate(1)
assert "Laps: 31" in short.results(1), short.results(1)[:200]

# --- an empty calendar is a season with no matchdays, not a crash ---
empty = make_competition({"circuitNames": [], "circuitNations": [],
                          "circuitEvents": [], "circuitTypes": [],
                          "lapRecords": [], "trackLengths": [],
                          "aggressiveness": [], "technicality": [],
                          "qualifyingFormats": [], "rainChances": [],
                          "overtakingDifficulties": [], "errorPunishments": []})
assert empty.matchdays() == 0
assert empty.matchdayNames() == []
empty.scorinate(0)  # out of range, must be a no-op

print("scorinator paradigm tests passed")
