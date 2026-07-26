"""The Racing Scorinator.

A port of the Google Sheets "Racing Scorinator", which simulates a racing
series one lap at a time. One call to scorinate() runs a single session
(practice, qualifying or race) of a single race weekend for the whole grid;
XkorSeasonCompetition drives it across a calendar and keeps the championship
standings.

The original's dice are RAND() cells whose *decimal digits* are chopped up
with LEFT/RIGHT/MID and summed. Those digit tricks are the whole source of
the model's distributions, so they are reproduced here rather than replaced
with equivalent-looking draws — see the _text/_digitSum helpers below. Google
Sheets renders RAND() at ten decimal places, which is what _text() produces;
the lap-time formula below reproduces the sheet's own cached lap times to
float precision.

The model is the original's, but three of its formulas are transcription slips
over an intent the surrounding formulas make unambiguous, and the port fixes
them rather than reproducing them. Each is argued at the site:

* the qualifying mistake test, which the original can never fail, and whose
  clean branch is missing a pair of brackets — see _bestOfThree()
* the experience and shared-nation scalings in the RP bonus, which the
  original applies to the engine term alone — see _rpBonus()
* the fourth elimination-qualifying session, a character-for-character copy of
  the third in the original — see _eliminationQualifying()

Anything else that reads oddly is deliberate and explained where it happens;
the safety-car rank in _safetyCarTime() is the one most likely to look like a
bug and isn't.
"""

import math
import sys

from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .abstractparadigm import XkorAbstractParadigm

DBL_MAX = sys.float_info.max

# Rand-matrix geometry, from the sheet: B37:BC66 are RAND() cells and
# BD37:CZ66 are pseudo-randoms spliced together out of earlier columns.
RAW_COLUMNS = 54
TOTAL_COLUMNS = 103
SPLICE_BACK_A = 50  # BD37 reads F37 …
SPLICE_BACK_B = 51  # … and E37
MATRIX_ROWS = 30  # rows 37–66

# Rows the sheet reads for series-wide (rather than per-driver) dice.
SPIN_MAGNITUDE_ROW = 14  # row 51
SAFETY_CAR_LENGTH_ROW = 27  # row 64
SAFETY_CAR_CHANCE_ROW = 28  # row 65
WEATHER_ROW = 19  # row 56
WEATHER_COLUMN = 6  # column H
TAIL_DIGIT_COLUMN = 6  # RIGHT(H37) in the tiered-qualifying formulas
QUALIFYING_MISTAKE_COLUMN = 72  # BV37, the die behind a scruffy qualifying lap

# The 2% a scruffy qualifying lap costs, and how much reliability protects
# against one: the die must beat R × this to be a mistake, so the more reliable
# the driver, the rarer it is.
QUALIFYING_MISTAKE_PENALTY = 1.02
QUALIFYING_MISTAKE_RELIABILITY = 0.125

# ED3:FG3 — the practice/qualifying flying-lap columns.
QUALIFYING_LAPS = 30
ONE_SHOT_LAPS = 4  # ED3:EG3
SECOND_TIER_FIRST_LAP = 8  # EK3:FG3

# Scorinate!C8:C9 — the weather roll and what it does to lap times.
CONDITION_MULTIPLIERS = {"Torrential Rain": 1.38, "Rainy": 1.15,
                         "Light Showers": 1.09, "Cloudy": 1.005, "Dry": 1.0}

RETIRED = "Retired"

# The neutral tyre and engine supplier: contributes nothing to any rating, so a
# series that doesn't model suppliers can leave those fields alone.
STOCK = "Stock"

# The season settings, straight off the block to the right of the sheet's Input
# tab. These are the fallbacks the paradigm uses when an event has not had its
# options edited yet; XkorScorinatorParadigmOptions seeds its widgets from the
# same dict, so an untouched season and a freshly-opened options page agree.
# Teams, tyre makers and engine makers are not here — they are entrants, and
# live on the participants step (see XkorScorinatorParticipantsWidget).
DEFAULTS = {
    "kmPerRace": 305,
    "speedPercent": 100,
    "driversOnGrid": 30,
    "spinConstant": 30,
    "spinMultiplier": 1.4,
    "crashConstant": 26,
    "crashMultiplier": 1.4,
    "eliteMultiplierQualifying": 1.5,
    "eliteMultiplierRace": 4.5,
    "safetyCar": "R",
    "homeBonusR": 1,
    "homeBonusA": 0.2,
    "homeBonusT": 0.2,
    "polePositionBonus": 0,
    "fastestLapBonus": 1,
    "showQuarterDistances": "Y",
    "useTyres": "Y",
    "useEngines": "Y",
    "ratingWeightDrivers": 0.5,
    "ratingWeightTeams": 1,
    "ratingWeightTyres": 1,
    "ratingWeightEngines": 1,
    "rpWeightDrivers": 1,
    "rpWeightTeams": 0.33,
    "rpWeightTyres": 0.1,
    "rpWeightEngines": 0.1,
    "experienceWeightDrivers": 0,
    "experienceWeightTeams": 0,
    "experienceWeightTyres": 0,
    "experienceWeightEngines": 0,
    "pointsPerPosition": [25, 18, 14, 10, 8, 6, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0,
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "alliances": [],
}


def defaultValue(key):
    value = DEFAULTS.get(key, [])
    return list(value) if isinstance(value, list) else value


def _text(x):
    """The text Google Sheets produces for a RAND() cell: ten decimal places,
    trailing zeros kept. RIGHT()/LEFT()/LEN() in the sheet all see this, so
    the digit arithmetic below depends on getting it right — confirmed against
    the sheet's own spliced-string cells, which round at the tenth decimal."""
    if isinstance(x, str):
        return x
    return "%.10f" % x


def _rawDigits(s):
    """The digit characters of a chopped-up cell, left exactly as the sheet's
    text functions hand them over — leading zeros included, because "0."&"06"
    is 0.006."""
    return "".join(c for c in s if c.isdigit())


def _digits(s):
    """VALUE() of a digit string, back as digits: leading zeros are lost. Only
    for the places where the sheet applies VALUE() before concatenating."""
    stripped = _rawDigits(s)
    if stripped == "":
        return ""
    return str(int(stripped))


def _digitSum(number, width):
    """SUMPRODUCT(1*MID(value, ROW(INDIRECT("1:"&width)), 1)) — the digits of
    `number`, summed, but only as far as `width` characters. Positions past
    the end of the number contribute nothing."""
    d = _digits(number)
    return sum(int(c) for c in d[:width])


def _spinNumber(cell):
    """SUMPRODUCT(1*MID(SUBSTITUTE(cell,".",0), …)) — the digit sum of the
    cell's decimals, the sheet's spin/mistake die."""
    t = _text(cell)
    return _digitSum(t.replace(".", "0"), len(t))


def _crashNumber(a, b, c):
    """The nine-digit crash die: LEFT(RIGHT(x,6),3) of three consecutive lap
    columns, concatenated and digit-summed."""
    piece = lambda x: _text(x)[-6:][:3]
    return _digitSum(piece(a) + piece(b) + piece(c), len(_text(a)))


def _leadingFraction(cell):
    """VALUE("0."&LEFT(RIGHT(cell,5),3)) — a three-digit fraction."""
    d = _digits(_text(cell)[-5:][:3])
    return float("0." + d) if d else 0.0


def _trailingFraction(cell):
    """VALUE("0.0"&RIGHT(cell,2)) — a small positive nudge."""
    d = _rawDigits(_text(cell)[-2:])
    return float("0.0" + d) if d else 0.0


def _trailingMultiplier(cell):
    """VALUE("1.0"&RIGHT(cell)) — the sheet's 1.00–1.09 slowdown factor."""
    d = _rawDigits(_text(cell)[-1:])
    return float("1.0" + d) if d else 1.0


def _trailingPair(cell):
    """VALUE(RIGHT(cell,2)) — an integer from 0 to 99."""
    d = _digits(_text(cell)[-2:])
    return int(d) if d else 0


def _trailingPairFraction(cell):
    """VALUE("0."&RIGHT(cell,2)) — the safety-car deployment die, which the
    sheet compares against 0.8."""
    d = _rawDigits(_text(cell)[-2:])
    return float("0." + d) if d else 0.0


def _median(values):
    if not values:
        return 0.0
    s = sorted(values)
    middle = len(s) // 2
    if len(s) % 2:
        return s[middle]
    return (s[middle - 1] + s[middle]) / 2.0


def _small(values, n):
    """SMALL(range, n) — the nth smallest. Returns None when the range is too
    short, which the sheet's IFERROR turns into a blank result."""
    if len(values) < n:
        return None
    return sorted(values)[n - 1]


class _Machine:
    """A team, tyre manufacturer or engine manufacturer: a name, a nation, an
    optional monogram and R/A/T/E ratings."""

    def __init__(self, name="", nation="", monogram="", r=0.0, a=0.0, t=0.0, e=0.0):
        self.name = name
        self.nation = nation
        self.monogram = monogram
        self.r = r
        self.a = a
        self.t = t
        self.e = e


class _Driver:
    """One entry on the grid, with its combined ratings resolved."""

    def __init__(self, athlete):
        self.athlete = athlete
        self.number = ""
        self.tla = ""
        self.team = _Machine()
        self.tyres = _Machine()
        self.engine = _Machine()
        self.rpBonus = 0.0
        self.r = 0.0
        self.a = 0.0
        self.t = 0.0
        self.experience = 0.0
        self.teammateFactor = 1.0
        self.home = False
        self.gridPosition = 0
        # per-session state
        self.laps = []  # lap times, or RETIRED
        self.retiredOnLap = 0
        self.totalTime = DBL_MAX
        self.qualifyingLaps = []


class XkorScorinatorParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["season"] = True
        self.supportedCompetitions["singleRace"] = True

    def defaultCompetition(self):
        return "season"

    def hasOptionsWidget(self):
        return True

    def newAthleteWidget(self):
        from ..signuplisteditor.scorinatorparticipantswidget import XkorScorinatorParticipantsWidget
        return XkorScorinatorParticipantsWidget()

    def newOptionsWidget(self, paradigmOptions):
        from .options.scorinatorparadigmoptions import XkorScorinatorParadigmOptions
        return XkorScorinatorParadigmOptions(paradigmOptions)

    # ------------------------------------------------------------------ options

    def _opt(self, key):
        """A season setting, falling back to the sheet's own value."""
        return self.userOpt.get(key, defaultValue(key))

    def _registry(self, athletes, kind):
        """The teams, tyre makers or engine makers on the entry list. They are
        participants like the drivers, entered on their own tab of the
        participants step and tagged with a `kind` property."""
        from ..signuplisteditor.scorinatorparticipantswidget import kindOf

        rval = []
        for a in athletes:
            if kindOf(a) != kind or not a.name:
                continue
            rval.append(_Machine(
                a.name, a.nation, toString(a.property("monogram")),
                toDouble(a.property("reliability")),
                toDouble(a.property("aggression")),
                toDouble(a.property("technique")),
                toDouble(a.property("experience"))))
        return rval

    def _lookup(self, registry, key):
        """Drivers name their tyres and engine by monogram in the sheet; accept
        the full name too, so hand-written signup lists work."""
        if not key:
            return None
        for i in registry:
            if i.monogram and i.monogram == key:
                return i
        for i in registry:
            if i.name == key:
                return i
        return None

    def _resolve(self, registry, athlete, property, description, stock=False):
        """Find what a driver says it is driving.

        Tyres and engines fall back to "Stock" — a neutral supplier that
        contributes nothing to any rating — when the field is blank or names it
        explicitly, so a series that doesn't model suppliers needs no entries at
        all. A team, or a supplier named but not entered, is a mistake worth
        seeing: it would quietly hobble the car, so it goes in the header."""
        key = toString(athlete.property(property))
        machine = self._lookup(registry, key)
        if machine is not None:
            return machine
        if stock and (not key or key.strip().lower() == STOCK.lower()):
            return _Machine(STOCK)
        if key:
            self.unmatched.append("%s: no %s called “%s” on the entry list"
                                  % (athlete.name, description, key))
        return _Machine()

    def _alliances(self):
        """Bi-national entities from the sheet's RP Bonus tab, as "AAA+BBB"
        strings: a driver from either nation counts as half-home in the
        other's race."""
        rval = []
        for i in toList(self._opt("alliances")):
            parts = [p.strip() for p in toString(i).replace("/", "+").split("+")]
            if len(parts) >= 2 and parts[0] and parts[1]:
                rval.append((parts[0], parts[1]))
        return rval

    def _isHalfHome(self, homeNation, nations):
        for a, b in self._alliances():
            for n in nations:
                if (a == homeNation and b == n) or (b == homeNation and a == n):
                    return True
        return False

    # ------------------------------------------------------------------ ratings

    def _rpBonus(self, driver, experience):
        """Standings!T — the combined RP bonus, weighted across the driver's
        own nation and those of its team and suppliers, then scaled by
        experience and discounted for a shared nation.

        In the original both of those scalings land on the engine term alone,
        because that is where its brackets close — so the same-nation discount
        came out as about 1% instead of 10%. Applying them to the whole sum is
        plainly what was meant."""
        rpDriver = toDouble(self._opt("rpWeightDrivers"))
        rpTeam = toDouble(self._opt("rpWeightTeams"))
        rpTyres = toDouble(self._opt("rpWeightTyres"))
        rpEngines = toDouble(self._opt("rpWeightEngines"))

        # the sheet's VALUE("1.00"&E) trick: experience nudges the engine term
        if experience > 99999.999:
            experienceFactor = toDouble("1." + toString(experience))
        elif experience > 9999.999:
            experienceFactor = toDouble("1.0" + toString(experience))
        else:
            experienceFactor = toDouble("1.00" + toString(experience))
        if experienceFactor == 0.0:
            experienceFactor = 1.0

        bonus = self._nationRP(driver.athlete.nation) * rpDriver
        bonus += self._nationRP(driver.team.nation) * rpTeam
        bonus += self._nationRP(driver.tyres.nation) * rpTyres
        bonus += self._nationRP(driver.engine.nation) * rpEngines
        return bonus * experienceFactor * driver.teammateFactor

    def _nationRP(self, nation):
        return toDouble(self.rpByNation.get(nation, 0.0))

    def _buildDrivers(self, athletes):
        from ..signuplisteditor.scorinatorparticipantswidget import kindOf

        teams = self._registry(athletes, "team")
        tyres = self._registry(athletes, "tyre")
        engines = self._registry(athletes, "engine")

        # the RP bonus comes from xkoranate's RP list, which has already been
        # folded into each entrant's rpBonus by XkorEvent::makeStartList().
        # Teams and suppliers are entrants too, so their nations get one — read
        # them before the field is narrowed to the drivers.
        self.rpByNation = {}
        for i in athletes:
            if i.nation and i.nation not in self.rpByNation:
                self.rpByNation[i.nation] = i.rpBonus

        # anything not entered as a team or a supplier is on the grid
        athletes = [a for a in athletes if kindOf(a) == "driver"]
        self.unmatched = []

        useTyres = toString(self._opt("useTyres")).upper().startswith("Y")
        useEngines = toString(self._opt("useEngines")).upper().startswith("Y")

        wDrivers = toDouble(self._opt("ratingWeightDrivers"))
        wTeams = toDouble(self._opt("ratingWeightTeams"))
        wTyres = toDouble(self._opt("ratingWeightTyres"))
        wEngines = toDouble(self._opt("ratingWeightEngines"))
        eDrivers = toDouble(self._opt("experienceWeightDrivers"))
        eTeams = toDouble(self._opt("experienceWeightTeams"))
        eTyres = toDouble(self._opt("experienceWeightTyres"))
        eEngines = toDouble(self._opt("experienceWeightEngines"))

        drivers = []
        for athlete in athletes:
            d = _Driver(athlete.clone())
            d.number = toString(athlete.property("number"))
            d.tla = toString(athlete.property("tla")) or athlete.name[0:3].upper()
            d.team = self._resolve(teams, athlete, "team", "team")
            if useTyres:
                d.tyres = self._resolve(tyres, athlete, "tyres", "tyre maker",
                                        stock=True)
            if useEngines:
                d.engine = self._resolve(engines, athlete, "engines",
                                         "engine maker", stock=True)
            drivers.append(d)

        # Standings!E4=E5 — the sheet discounts a driver whose nation matches
        # the next row's, which is how it stops paired entries double-counting
        for i in range(len(drivers)):
            nextNation = drivers[i + 1].athlete.nation if i + 1 < len(drivers) else None
            drivers[i].teammateFactor = 0.9 if drivers[i].athlete.nation == nextNation else 1.0

        # experience first: the RP bonus reads it
        for d in drivers:
            d.experience = (toDouble(d.athlete.property("experience")) * eDrivers
                            + d.team.e * eTeams
                            + d.tyres.e * eTyres
                            + d.engine.e * eEngines * 10000)

        for d in drivers:
            d.rpBonus = self._rpBonus(d, d.experience)

        medianRP = _median([d.rpBonus for d in drivers])
        for d in drivers:
            adjustment = d.rpBonus * 0.005 - medianRP * 0.005
            d.r = (toDouble(d.athlete.property("reliability")) * wDrivers
                   + d.team.r * wTeams + d.tyres.r * wTyres
                   + d.engine.r * wEngines + adjustment)
            # A and T both take half of the tyres' T rating, as in the sheet
            d.a = (toDouble(d.athlete.property("aggression")) * wDrivers
                   + d.team.a * wTeams + d.tyres.t * wTyres * 0.5
                   + d.engine.a * wEngines + adjustment)
            d.t = (toDouble(d.athlete.property("technique")) * wDrivers
                   + d.team.t * wTeams + d.tyres.t * wTyres * 0.5
                   + d.engine.t * wEngines + adjustment)

        return drivers

    def _applyHomeBonus(self, drivers, homeNation):
        """Calculation!L3:N3 — a full home bonus for the host nation's own
        drivers and teams, half for an allied nation."""
        homeR = toDouble(self._opt("homeBonusR"))
        homeA = toDouble(self._opt("homeBonusA"))
        homeT = toDouble(self._opt("homeBonusT"))

        for d in drivers:
            nations = (d.athlete.nation, d.team.nation)
            if homeNation and homeNation in nations:
                d.r += homeR
                d.a += homeA
                d.t += homeT
                d.home = True
            elif homeNation and self._isHalfHome(homeNation, nations):
                d.r += homeR * 0.5
                d.a += homeA * 0.5
                d.t += homeT * 0.5
                d.home = True
            else:
                d.home = False

    # ------------------------------------------------------------------- dice

    def _makeMatrix(self, rows):
        """B37:CZ66 — RAW_COLUMNS of RAND() per driver, then the spliced
        pseudo-random columns that carry the sheet past lap 54."""
        rows = max(rows, MATRIX_ROWS)
        matrix = []
        for _ in range(rows):
            row = [_text(self.s.randUniform()) for _ in range(RAW_COLUMNS)]
            for j in range(RAW_COLUMNS, TOTAL_COLUMNS):
                row.append("0." + row[j - SPLICE_BACK_A][-5:]
                           + row[j - SPLICE_BACK_B][-6:][:5])
            matrix.append(row)
        return matrix

    def _die(self, row, column):
        """One cell of the matrix, clamped so long races can't run off the
        end of the sheet's columns."""
        return self.matrix[row % len(self.matrix)][column % TOTAL_COLUMNS]

    def _conditions(self, rainChance):
        r = _trailingPair(self._die(WEATHER_ROW, WEATHER_COLUMN))
        if r < rainChance * 0.05:
            return "Torrential Rain"
        elif r < rainChance * 0.5:
            return "Rainy"
        elif r < rainChance:
            return "Light Showers"
        elif r < rainChance * 2:
            return "Cloudy"
        return "Dry"

    def _marginForError(self, laps, errorPunishment, conditionMultiplier):
        """Calculation!U34:DO34 — the margin starts at the circuit's error
        punishment, decays over the first dozen laps and then creeps back up
        once the tyres are past 60% distance."""
        floorValue = conditionMultiplier * 2 - 1
        margins = [0.0] * (laps + 4)
        if laps + 4 > 1:
            margins[1] = errorPunishment
        for n in range(2, min(13, laps + 4)):
            margins[n] = floorValue if margins[n - 1] <= floorValue + 1 else margins[n - 1] - 1
        for n in range(13, laps + 4):
            if n > laps * 0.6:
                margins[n] = margins[n - 1] + floorValue * 0.008
            else:
                margins[n] = margins[n - 1]
        return margins

    # -------------------------------------------------------------- scorinate

    def scorinate(self, athletes, previousResults=None):
        self.out = []
        self.res = []
        self.header = []
        self.safetyCarLaps = []
        self.quarterOrders = {}

        session = toString(self.userOpt.get("session", "race")).lower()
        drivers = self._buildDrivers(athletes)

        # circuit
        lapRecord = toDouble(self.userOpt.get("lapRecord", 60))
        trackLength = toDouble(self.userOpt.get("trackLength", 4))
        speedPercent = toDouble(self._opt("speedPercent")) or 100.0
        kmPerRace = toDouble(self._opt("kmPerRace"))
        self.trackAggression = toDouble(self.userOpt.get("aggressiveness", 5)) * 0.1
        self.trackTechnique = toDouble(self.userOpt.get("technicality", 5)) * 0.1
        self.overtakingDifficulty = toDouble(self.userOpt.get("overtakingDifficulty", 2))
        self.errorPunishment = toDouble(self.userOpt.get("errorPunishment", 2))
        rainChance = toDouble(self.userOpt.get("rainChance", 3))
        homeNation = toString(self.userOpt.get("homeNation", ""))
        self.qualifyingFormat = toString(self.userOpt.get("qualifyingFormat", "Trad"))

        self._applyHomeBonus(drivers, homeNation)

        self.driversOnGrid = toInt(self._opt("driversOnGrid")) or len(drivers)
        self.baseLap = lapRecord * 100.0 / speedPercent
        self.laps = max(1, int(kmPerRace / trackLength) + 1) if trackLength else 1

        self.matrix = self._makeMatrix(len(drivers))
        self.conditions = self._conditions(rainChance)
        self.conditionMultiplier = CONDITION_MULTIPLIERS[self.conditions]
        # the parade lap doubles as the sheet's "botched lap" fallback time
        self.paradeLap = (self.baseLap * 1.05) * self.conditionMultiplier + self.baseLap * 0.25
        self.margins = self._marginForError(max(self.laps, QUALIFYING_LAPS),
                                           self.errorPunishment,
                                           self.conditionMultiplier)
        self.spinConstant = toDouble(self._opt("spinConstant"))
        self.spinMultiplier = toDouble(self._opt("spinMultiplier"))
        self.crashConstant = toDouble(self._opt("crashConstant"))
        self.crashMultiplier = toDouble(self._opt("crashMultiplier"))
        self.safetyCarType = toString(self._opt("safetyCar")).upper()[0:1] or "R"

        if session == "race":
            self._runRace(drivers)
        else:
            self._runQualifying(drivers, session)

        self.generateOutput()

    # -------------------------------------------------------------- qualifying

    def _qualifyingLapCount(self, driver, session):
        """Calculation!EC — better drivers get more flying laps, the host
        nation's drivers get four more, and elimination qualifying adds a
        block of twenty for its extra sessions."""
        base = int(4 + driver.r) if driver.home else int(driver.r)
        count = base * 3 - 1
        if self.qualifyingFormat.upper() == "E":
            count += 20 * (0 if session == "practice" else 1)
        return max(0, min(count, QUALIFYING_LAPS))

    def _qualifyingTime(self, driver, row, lap, session):
        """Calculation!ED3 — one flying lap."""
        die = self._die(row, lap - 1)
        margin = self.margins[lap] if lap < len(self.margins) else 0.0
        eliteMultiplier = toDouble(self._opt("eliteMultiplierQualifying"))

        if _spinNumber(die) < (self.spinConstant + margin / 2 - driver.r * self.spinMultiplier):
            magnitude = _leadingFraction(self._die(SPIN_MAGNITUDE_ROW, lap - 1))
            time = self.paradeLap + magnitude * (self.errorPunishment * (11 - driver.r))
        else:
            exponent = (driver.a * self.trackAggression
                        + driver.t * self.trackTechnique) * 0.3
            time = (self.baseLap * self.conditionMultiplier
                    + (self.baseLap / (eliteMultiplier + 1.5))
                    * math.pow(toDouble(die), exponent))
            # the trailing nudge is divided by the driver's reliability here,
            # unlike in the race formula
            if driver.r * 0.5:
                time += _trailingFraction(die) / (driver.r * 0.5)
        return time * (1.05 if session == "practice" else 1.0)

    def _bestOfThree(self, driver, row, multiplier=1.0, offset=0, count=None):
        """A qualifying time: the mean of a driver's three best laps in the
        window, 2% slower if it rolls a scruffy one.

        The original never actually applies that penalty — it tests a text cell
        against a number, and a spreadsheet sorts text above every number, so
        the test is always true and every driver takes the 2%. Its clean branch
        is also missing a pair of brackets, which would have made a clean lap
        two laps long. Both are transcription slips over an unambiguous intent,
        so the port rolls the die properly and averages the three laps."""
        laps = driver.qualifyingLaps
        window = laps[offset:offset + count] if count else laps[offset:]
        best = [_small(window, i) for i in (1, 2, 3)]
        if any(i is None for i in best):
            return None
        time = sum(best) / 3.0 * multiplier
        if self._madeMistake(driver, row):
            time *= QUALIFYING_MISTAKE_PENALTY
        return time

    def _madeMistake(self, driver, row):
        die = toDouble(self._die(row, QUALIFYING_MISTAKE_COLUMN))
        return die > driver.r * QUALIFYING_MISTAKE_RELIABILITY

    def _meanOfPair(self, laps, a, b, multiplier=1.0):
        first, second = _small(laps, a), _small(laps, b)
        if first is None or second is None:
            return None
        return (first + second) / 2.0 * multiplier

    def _rankAscending(self, values):
        """RANK(x, range, 1) — ties share the better rank, blanks get None."""
        ranked = sorted(i for i in values if i is not None)
        rval = []
        for v in values:
            rval.append(ranked.index(v) + 1 if v is not None else None)
        return rval

    def _runQualifying(self, drivers, session):
        for index, d in enumerate(drivers):
            count = self._qualifyingLapCount(d, session)
            d.qualifyingLaps = [self._qualifyingTime(d, index, lap + 1, session)
                                for lap in range(count)]

        fmt = self.qualifyingFormat.upper()
        if session == "practice" or fmt not in ("OS", "TT", "E"):
            times = [self._bestOfThree(d, i) for i, d in enumerate(drivers)]
            sessionNames = ["Practice" if session == "practice" else "Qualifying"]
            sessionTimes = [times]
        elif fmt == "OS":
            times = [self._bestOfThree(d, i, count=ONE_SHOT_LAPS)
                     for i, d in enumerate(drivers)]
            sessionNames = ["One-shot qualifying"]
            sessionTimes = [times]
        elif fmt == "TT":
            times, sessionNames, sessionTimes = self._twoTierQualifying(drivers)
        else:
            times, sessionNames, sessionTimes = self._eliminationQualifying(drivers)

        positions = self._rankAscending(times)
        best = min((t for t in times if t is not None), default=None)

        for index, d in enumerate(drivers):
            r = XkorResult()
            r.athlete = d.athlete.clone()
            time = times[index]
            r.result["session"] = session
            r.result["number"] = d.number
            r.result["tla"] = d.tla
            r.result["team"] = d.team.name
            r.result["engine"] = d.engine.name
            r.result["tyres"] = d.tyres.name
            r.result["conditions"] = self.conditions
            r.result["gridPosition"] = positions[index] or 0
            r.result["sessionTimes"] = [s[index] for s in sessionTimes]
            r.result["sessionNames"] = sessionNames
            if time is None:
                r.setScore(DBL_MAX)
                r.setScoreString("no time")
            else:
                r.setScore(time)
                r.setScoreString(self.timeFormat(time, 3))
                r.result["gap"] = time - best
            self.res.append(r)

        self._sortByPosition()
        self._buildQualifyingOutput(session)

    def _twoTierQualifying(self, drivers):
        """Calculation!FN:FR — everyone runs, then the top ten run again on
        the laps from the eighth onward."""
        advance = 10
        first = [self._bestOfThree(d, i, multiplier=1.0006)
                 for i, d in enumerate(drivers)]
        firstRanks = self._rankAscending(first)

        second = []
        for index, d in enumerate(drivers):
            rank = firstRanks[index]
            if rank is not None and rank < advance + 1:
                second.append(self._bestOfThree(
                    d, index, offset=SECOND_TIER_FIRST_LAP - 1))
            elif first[index] is not None:
                second.append(first[index] * _trailingMultiplier(
                    self._die(index, TAIL_DIGIT_COLUMN)))
            else:
                second.append(None)
        secondRanks = self._rankAscending(second)

        final = []
        for index in range(len(drivers)):
            if firstRanks[index] is None:
                final.append(None)
            elif firstRanks[index] > advance:
                # eliminated: keep the first-session time so the order holds
                final.append(first[index])
            else:
                final.append(second[index])
        # rank on the merged column the way the sheet does: eliminated drivers
        # keep their first-session position, qualifiers are re-ranked
        merged = [None] * len(drivers)
        qualifierOrder = [i for i in range(len(drivers))
                          if firstRanks[i] is not None and firstRanks[i] <= advance]
        qualifierOrder.sort(key=lambda i: (secondRanks[i] is None, secondRanks[i] or 0))
        for position, i in enumerate(qualifierOrder):
            merged[i] = position + 1
        nextPosition = len(qualifierOrder) + 1
        for i in sorted((i for i in range(len(drivers)) if merged[i] is None
                         and firstRanks[i] is not None),
                        key=lambda i: firstRanks[i]):
            merged[i] = nextPosition
            nextPosition += 1
        self._forcedPositions = merged
        return final, ["Q1", "Q2"], [first, second]

    def _eliminationQualifying(self, drivers):
        """Calculation!FS:GC — four sessions, cutting to 75%, 50% and 25% of
        the grid, each run on a better pair of the driver's laps than the last.

        The original's fourth session is a copy of its third, down to the
        character, so the pair it should have moved on to — a driver's two best
        laps — went unused. The progression makes the intended value plain."""
        cuts = [int(self.driversOnGrid * 0.75), int(self.driversOnGrid * 0.5),
                int(self.driversOnGrid * 0.25)]
        pairs = [(8, 7, 1.0), (6, 5, 1.014), (4, 3, 1.01), (2, 1, 1.0)]

        sessionTimes = []
        sessionRanks = []
        for stage, (a, b, multiplier) in enumerate(pairs):
            times = []
            for index, d in enumerate(drivers):
                if stage == 0:
                    times.append(self._meanOfPair(d.qualifyingLaps, a, b, multiplier))
                    continue
                previousRank = sessionRanks[stage - 1][index]
                if previousRank is not None and previousRank <= cuts[stage - 1]:
                    times.append(self._meanOfPair(d.qualifyingLaps, a, b, multiplier))
                elif sessionTimes[stage - 1][index] is not None:
                    times.append(sessionTimes[stage - 1][index]
                                 * _trailingMultiplier(self._die(index, TAIL_DIGIT_COLUMN)))
                else:
                    times.append(None)
            ranks = self._rankAscending(times)
            if stage > 0:
                # a driver knocked out of the previous session keeps its place
                ranks = [sessionRanks[stage - 1][i]
                         if (sessionRanks[stage - 1][i] is not None
                             and sessionRanks[stage - 1][i] > cuts[stage - 1])
                         else ranks[i]
                         for i in range(len(drivers))]
            sessionTimes.append(times)
            sessionRanks.append(ranks)

        self._forcedPositions = sessionRanks[-1]
        return sessionTimes[-1], ["Q1", "Q2", "Q3", "Q4"], sessionTimes

    # -------------------------------------------------------------------- race

    def _gridFigure(self, driver):
        """Calculation!S3 — the time a driver concedes for starting further
        back, which the overtaking difficulty amplifies."""
        return (driver.gridPosition - 1) * self.overtakingDifficulty

    def _raceTime(self, driver, row, lap, previous, safetyCarActive, cumulative,
                  leaderCumulative, allCumulative):
        """Calculation!U3 — one racing lap, or RETIRED."""
        margin = self.margins[lap] if lap < len(self.margins) else 0.0
        eliteMultiplier = toDouble(self._opt("eliteMultiplierRace")) or 1.0

        crash = _crashNumber(self._die(row, lap - 1), self._die(row, lap),
                             self._die(row, lap + 1))
        if crash < (self.crashConstant + margin - driver.r * self.crashMultiplier):
            return RETIRED

        if safetyCarActive:
            if self.safetyCarType == "V":
                return self.baseLap * 1.05 + 25
            return self._safetyCarTime(cumulative, leaderCumulative, allCumulative)

        die = self._die(row, lap - 1)
        if _spinNumber(die) < (self.spinConstant + margin / 2
                               - driver.r * self.spinMultiplier):
            magnitude = _leadingFraction(self._die(SPIN_MAGNITUDE_ROW, lap - 1))
            return previous + magnitude * (self.errorPunishment * (11 - driver.r))

        exponent = (driver.a * self.trackAggression
                    + driver.t * self.trackTechnique) * 0.3
        time = ((self.baseLap * 1.05) * self.conditionMultiplier
                + ((self.baseLap * 1.05) / eliteMultiplier)
                * math.pow(toDouble(die), exponent)
                + _trailingFraction(die))
        # the sheet's pit-stop windows, at a third and two thirds distance
        if lap in (int(self.laps * 0.33), int(self.laps * 0.66)):
            time += 45 - driver.r
        return time

    def _safetyCarTime(self, cumulative, leaderCumulative, allCumulative):
        """Calculation!DB69 — under a real safety car the field concertinas up
        behind the leader.

        RANK() with no order argument counts down, so the rank here is 1 for the
        slowest car and highest for the leader. That looks like an oversight over
        elapsed times, but it is what makes the field close up: the added term
        is largest for the leader and smallest for the backmarkers. Ranking the
        other way would spread the field out under a safety car, so this stands
        as it is."""
        if cumulative is None or leaderCumulative is None:
            return self.paradeLap * 1.8
        gap = cumulative - leaderCumulative
        if gap == 0 or gap > (self.baseLap * self.conditionMultiplier) * 1.07:
            return self.paradeLap * 1.8
        rank = 1 + sum(1 for i in allCumulative if i is not None and i > cumulative)
        value = (self.paradeLap * 1.8 - gap
                 + (1 + self.overtakingDifficulty / 7.5) * rank)
        return self.paradeLap * 1.8 if value < self.paradeLap else value

    def _runRace(self, drivers):
        self._assignGrid(drivers)
        starters = [d for d in drivers if 0 < d.gridPosition <= self.driversOnGrid]
        nonStarters = [d for d in drivers if d not in starters]

        rows = {id(d): i for i, d in enumerate(drivers)}
        cumulative = {id(d): self.paradeLap for d in starters}
        previous = {id(d): self.paradeLap for d in starters}
        retired = {id(d): False for d in starters}

        safetyCarCounter = 0
        self.safetyCarLaps = []
        retiredCount = 0
        # Calculation!DP:EA — the sheet reports the order at each quarter
        quarters = [int(self.laps * fraction) for fraction in (0.25, 0.5, 0.75)]
        self.quarterOrders = {}

        for lap in range(1, self.laps + 1):
            safetyCarActive = safetyCarCounter > 0
            if safetyCarActive:
                self.safetyCarLaps.append(lap)
            leader = min((cumulative[id(d)] for d in starters
                          if not retired[id(d)] and cumulative[id(d)] is not None),
                         default=None)
            snapshot = [cumulative[id(d)] for d in starters if not retired[id(d)]]

            for d in starters:
                if retired[id(d)]:
                    d.laps.append(RETIRED)
                    continue
                time = self._raceTime(d, rows[id(d)], lap, previous[id(d)],
                                      safetyCarActive, cumulative[id(d)],
                                      leader, snapshot)
                if time == RETIRED:
                    retired[id(d)] = True
                    d.retiredOnLap = lap
                    d.laps.append(RETIRED)
                    continue
                d.laps.append(time)
                previous[id(d)] = time
                cumulative[id(d)] = ((1 + self.overtakingDifficulty / 7.5)
                                     * self._gridFigure(d)
                                     + sum(i for i in d.laps if i != RETIRED))

            # Calculation!U36 — a new retirement can bring the safety car out
            newRetiredCount = sum(1 for d in starters if retired[id(d)])
            if safetyCarCounter > 0:
                safetyCarCounter -= 1
            elif newRetiredCount > retiredCount:
                if _trailingPairFraction(self._die(SAFETY_CAR_CHANCE_ROW, lap - 1)) > 0.8:
                    tail = _digits(_text(self._die(SAFETY_CAR_LENGTH_ROW, lap - 1))[-1:])
                    safetyCarCounter = int(int(tail or 0) / 2)
            retiredCount = newRetiredCount

            if lap in quarters:
                self.quarterOrders[lap] = self._orderAt(starters, lap)

        self._finishRace(starters, nonStarters, cumulative)

    def _orderAt(self, starters, lap):
        """Calculation!DQ/DU/DY — the running order after a given lap."""
        standing = []
        for d in starters:
            if RETIRED in d.laps[:lap]:
                continue
            elapsed = sum(i for i in d.laps[:lap] if i != RETIRED)
            standing.append((elapsed + (1 + self.overtakingDifficulty / 7.5)
                             * self._gridFigure(d), d))
        standing.sort(key=lambda i: i[0])
        return [d for _, d in standing]

    def _assignGrid(self, drivers):
        """Grid positions come from the week's qualifying, which the season
        competition hands over as a list of athlete ids in grid order. Without
        one, the signup order is the grid."""
        order = [toString(i) for i in toList(self.userOpt.get("startingGrid", []))]
        if order:
            byId = {toString(d.athlete.id): d for d in drivers}
            position = 0
            for i in order:
                if i in byId:
                    position += 1
                    byId[i].gridPosition = position
            for d in drivers:
                if d.gridPosition == 0:
                    position += 1
                    d.gridPosition = position
        else:
            for index, d in enumerate(drivers):
                d.gridPosition = index + 1

    def _finishRace(self, starters, nonStarters, cumulative):
        points = [toDouble(i) for i in toList(
            self._opt("pointsPerPosition"))]
        fastestLapBonus = toDouble(self._opt("fastestLapBonus"))

        allLaps = [i for d in starters for i in d.laps if i != RETIRED]
        averageLap = sum(allLaps) / len(allLaps) if allLaps else self.baseLap

        finishers = [d for d in starters if d.retiredOnLap == 0]
        for d in finishers:
            d.totalTime = cumulative[id(d)]
        finishers.sort(key=lambda d: d.totalTime)
        winnerTime = finishers[0].totalTime if finishers else 0.0

        # the fastest lap of the race, for the bonus point
        fastestDriver, fastestTime = None, None
        for d in starters:
            laps = [i for i in d.laps if i != RETIRED]
            if laps and (fastestTime is None or min(laps) < fastestTime):
                fastestDriver, fastestTime = d, min(laps)

        for position, d in enumerate(finishers, start=1):
            r = self._raceResult(d)
            r.result["position"] = position
            r.setScore(d.totalTime)
            gap = d.totalTime - winnerTime
            lapsDown = int(gap / averageLap) if averageLap else 0
            r.result["gap"] = gap
            r.result["lapsDown"] = lapsDown
            if position == 1:
                r.setScoreString(self.timeFormat(d.totalTime, 3))
            elif lapsDown >= 1:
                r.setScoreString("+%d lap%s" % (lapsDown, "" if lapsDown == 1 else "s"))
            else:
                r.setScoreString("+" + self.timeFormat(gap, 3))
            scored = points[position - 1] if position <= len(points) else 0.0
            if d is fastestDriver:
                scored += fastestLapBonus
                r.result["fastestLap"] = fastestTime
            r.result["points"] = scored
            self.res.append(r)

        for d in starters:
            if d.retiredOnLap == 0:
                continue
            r = self._raceResult(d)
            r.result["position"] = 0
            r.result["retiredOnLap"] = d.retiredOnLap
            r.result["points"] = 0.0
            r.setScore(DBL_MAX)
            r.setScoreString("Ret. lap %d" % d.retiredOnLap)
            if d is fastestDriver:
                r.result["fastestLap"] = fastestTime
            self.res.append(r)

        for d in nonStarters:
            r = self._raceResult(d)
            r.result["position"] = 0
            r.result["points"] = 0.0
            r.setScore(DBL_MAX)
            r.setScoreString("DNS")
            self.res.append(r)

        self._buildRaceOutput(finishers)

    def _raceResult(self, driver):
        r = XkorResult()
        r.athlete = driver.athlete.clone()
        r.result["session"] = "race"
        r.result["number"] = driver.number
        r.result["tla"] = driver.tla
        r.result["team"] = driver.team.name
        r.result["engine"] = driver.engine.name
        r.result["tyres"] = driver.tyres.name
        r.result["gridPosition"] = driver.gridPosition
        r.result["conditions"] = self.conditions
        laps = [i for i in driver.laps if i != RETIRED]
        if laps:
            r.result["bestLap"] = min(laps)
            r.result["lapsCompleted"] = len(laps)
        return r

    # ------------------------------------------------------------------ output

    def _sortByPosition(self):
        forced = getattr(self, "_forcedPositions", None)
        if forced:
            for index, r in enumerate(self.res):
                if index < len(forced) and forced[index]:
                    r.result["gridPosition"] = forced[index]
            self._forcedPositions = None
        self.res.sort(key=lambda r: (r.result.get("gridPosition") or 10 ** 6,
                                     r.score()))

    def _warnings(self):
        """Entry-list problems worth putting in front of the user, deduplicated
        and capped so one mistyped team name in a thirty-car field doesn't bury
        the classification."""
        seen = []
        for i in self.unmatched:
            if i not in seen:
                seen.append(i)
        if not seen:
            return []
        rval = ["Check the entry list:"]
        rval += ["  " + i for i in seen[:5]]
        if len(seen) > 5:
            rval.append("  …and %d more" % (len(seen) - 5))
        rval.append("")
        return rval

    def _nameWidth(self):
        return toInt(self.userOpt.get("nameWidth", 20)) + 2

    def _buildQualifyingOutput(self, session):
        nameWidth = self._nameWidth()
        teamWidth = toInt(self.userOpt.get("teamWidth", 22))
        header = "%-4s %-3s %-4s %s %s %10s %9s" % (
            "Pos", "#", "DRV", "Driver".ljust(nameWidth),
            "Team".ljust(teamWidth), "Time", "Gap")
        self.header = self._warnings() + ["Conditions: " + self.conditions, header]

        for r in self.res:
            position = r.result.get("gridPosition") or 0
            gap = r.result.get("gap")
            line = "%-4s %-3s %-4s %s %s %10s %9s" % (
                position or "—",
                toString(r.result.get("number")),
                toString(r.result.get("tla")),
                self.formatName(r.athlete).ljust(nameWidth)[:nameWidth],
                toString(r.result.get("team")).ljust(teamWidth)[:teamWidth],
                r.scoreString(),
                "" if gap is None or position == 1 else "+" + self.timeFormat(gap, 3))
            r.setOutput(line.rstrip())

    def _buildRaceOutput(self, finishers):
        nameWidth = self._nameWidth()
        teamWidth = toInt(self.userOpt.get("teamWidth", 22))
        header = "%-4s %-4s %-3s %-4s %s %s %13s %5s %s" % (
            "Pos", "Grid", "#", "DRV", "Driver".ljust(nameWidth),
            "Team".ljust(teamWidth), "Time", "Pts", "FL")
        self.header = self._warnings() + ["Conditions: " + self.conditions,
                                         "Laps: %d" % self.laps, header]
        if self.safetyCarLaps:
            self.header.insert(2, "Safety car: lap%s %s" % (
                "" if len(self.safetyCarLaps) == 1 else "s",
                ", ".join(str(i) for i in self.safetyCarLaps)))

        for r in self.res:
            position = r.result.get("position") or 0
            points = r.result.get("points") or 0
            line = "%-4s %-4s %-3s %-4s %s %s %13s %5s %s" % (
                position or "—",
                r.result.get("gridPosition") or "—",
                toString(r.result.get("number")),
                toString(r.result.get("tla")),
                self.formatName(r.athlete).ljust(nameWidth)[:nameWidth],
                toString(r.result.get("team")).ljust(teamWidth)[:teamWidth],
                r.scoreString(),
                "" if points == 0 else ("%g" % points),
                "✱" if "fastestLap" in r.result else "")
            r.setOutput(line.rstrip())

    def generateOutput(self):
        self.out = []
        for line in getattr(self, "header", []):
            self.out.append(("", line))
        for r in self.res:
            if r.output() != "":
                self.out.append((r.athlete.name, r.output()))

    # protected:

    def individualResult(self, athlete, type=None):
        return XkorResult(0, ath=athlete)
