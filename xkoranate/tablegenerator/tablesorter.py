import functools
import locale
import random
import sys
from operator import methodcaller

from .pointsscheme import XkorPointsAccessors, XkorPointsScheme

# a flip is saved through qNumber(), which writes 6 significant digits — so it
# has to be a whole number below a million to reload as the value that was
# written. Two teams sharing a value would tie in the sort that's meant to be
# the last resort, so values are drawn without repeats rather than trusted to
# be distinct by luck.
_MAX_FLIP = 999999


def assignCoinFlips(rows, coinFlips):
    """Give every row in `rows` a coin-flip value in `coinFlips` (keyed by
    team name), flipping a fresh one only the first time a team is seen.
    `coinFlips` is mutated in place and is expected to be the table's own
    persisted store, so a team's flip result — once made — sticks for as
    long as the table file does, surviving regenerating the table or
    relaunching the app, the same way a real coin toss wouldn't be redone
    just because someone looked at the standings again."""
    taken = set(coinFlips.values())
    for r in rows:
        if r.name() not in coinFlips:
            value = random.randint(0, _MAX_FLIP)
            while value in taken:
                value = random.randint(0, _MAX_FLIP)
            coinFlips[r.name()] = value
            taken.add(value)


def pruneCoinFlips(teamNames, coinFlips):
    """Drop flips for teams the table no longer has, so renaming a team over
    and over doesn't grow the saved file without bound. Mutates in place."""
    teamNames = set(teamNames)
    for name in [n for n in coinFlips if n not in teamNames]:
        del coinFlips[name]


# A sort rule takes the sorter and the rows being sorted and returns the
# (gr, eq) pair privateSort() ranks them with.

LOWER = True  # for rules where fewer ranks higher


def _ranked(value, lowerIsBetter=False):
    if lowerIsBetter:
        return (lambda a, b: value(a) < value(b)), (lambda a, b: value(a) == value(b))
    return (lambda a, b: value(a) > value(b)), (lambda a, b: value(a) == value(b))


def _rule(value, lowerIsBetter=False):
    """Rank rows on value(row); a string names an XkorTableRow method."""
    if isinstance(value, str):
        value = methodcaller(value)
    return lambda sorter, rows: _ranked(value, lowerIsBetter)


def _h2hRule(method, lowerIsBetter=False):
    """Rank rows on an XkorTableRow h2h method, which counts only the games
    between the rows being sorted."""
    def rule(sorter, rows):
        teams = [r.name() for r in rows]
        return _ranked(methodcaller(method, teams), lowerIsBetter)
    return rule


def _goalAverage(r):
    return sys.float_info.max if r.goalsAgainst() == 0 else r.goalsFor() / r.goalsAgainst()


def _otAndSOWins(r):
    # despite its name "otWins" counts shootout wins too; a league that wants
    # them apart ranks on "Regulation wins" instead. It keeps the key because
    # that string is what already-saved table files store.
    return r.otWins() + r.soWins()


def _winPercent(r):
    return 0 if r.played() == 0 else (r.wins() + r.draws() / 2) / r.played()


def _winPercentPure(r):
    return 0 if r.played() == 0 else r.wins() / r.played()


def _winPercentNFL(r):
    return 0 if r.played() == 0 else r.wins() / (r.wins() + r.losses())


def _coinFlip(sorter, rows):
    assignCoinFlips(rows, sorter.coinFlips)
    flips = sorter.coinFlips
    return _ranked(lambda r: flips[r.name()])


def _points(sorter, rows):
    return _ranked(sorter.points.pointsFor)


def _alphabetical(sorter, rows):
    # QString::localeAwareCompare(a.name(), b.name()) < 0; if we're sorting
    # on alphabetical order, the teams are tied!
    return (lambda a, b: locale.strcoll(a.name(), b.name()) < 0), (lambda a, b: True)


# id -> (label, rule), in the order the sort criteria widget offers them.
# The ids are what table files and events store.
SORT_RULES = {
    "awayGoals": ("Away goals", _rule("awayGoals")),
    "awayWins": ("Away wins", _rule("awayWins")),
    "coinFlip": ("Coin flip", _coinFlip),
    "goalAverage": ("Goal average", _rule(_goalAverage)),
    "goalDifference": ("Goal difference", _rule("goalDifference")),
    "goalsAgainst": ("Goals against", _rule("goalsAgainst", LOWER)),
    "goalsFor": ("Goals for", _rule("goalsFor")),
    "h2hAwayGoals": ("Head-to-head away goals", _h2hRule("h2hAwayGoals")),
    "h2hGoalDifference": ("Head-to-head goal difference", _h2hRule("h2hGoalDifference")),
    "h2hGoalsAgainst": ("Head-to-head goals against", _h2hRule("h2hGoalsAgainst", LOWER)),
    "h2hGoalsFor": ("Head-to-head goals for", _h2hRule("h2hGoalsFor")),
    "h2hPoints": ("Head-to-head points", _h2hRule("h2hPoints")),
    "h2hWins": ("Head-to-head wins", _h2hRule("h2hWins")),
    "homeGoalsAgainst": ("Home goals conceded", _rule("homeGoalsAgainst", LOWER)),
    "homeLosses": ("Home losses", _rule("homeLosses", LOWER)),
    "losses": ("Losses", _rule("losses", LOWER)),
    "otWins": ("Overtime/shootout wins", _rule(_otAndSOWins)),
    "points": ("Points", _points),
    "regulationWins": ("Regulation wins", _rule("regulationWins")),
    "winPercent": ("Win percentage (draws count 50%)", _rule(_winPercent)),
    "winPercentPure": ("Win percentage (draws count 0%)", _rule(_winPercentPure)),
    "winPercentNFL": ("Win percentage (draws ignored)", _rule(_winPercentNFL)),
    "wins": ("Wins", _rule("wins")),
}


class XkorTableSorter(XkorPointsAccessors):
    def __init__(self, points=None):
        # a table passes its own scheme, so the two always agree
        self.points = points if points is not None else XkorPointsScheme()
        # team name -> coin-flip value; a team's flip sticks once made, so
        # regenerating the table (or reloading it after a save) doesn't
        # re-roll it — see XkorTable.getCoinFlips()/setCoinFlips()
        self.coinFlips = {}

    def getCoinFlips(self):
        return self.coinFlips

    def pruneCoinFlips(self, teamNames):
        pruneCoinFlips(teamNames, self.coinFlips)

    def setCoinFlips(self, flips):
        self.coinFlips = flips

    def sort(self, rows, sortType):
        if sortType == "alphabetical":
            rule = _alphabetical
        elif sortType in SORT_RULES:
            rule = SORT_RULES[sortType][1]
        else:
            return [list(rows)]
        gr, eq = rule(self, rows)
        return self.privateSort(rows, gr, eq)

    def privateSort(self, rows, gr, eq):
        rval = []
        if len(rows) > 1:
            # sort and place into bins
            rows = sorted(rows, key=functools.cmp_to_key(
                lambda a, b: -1 if gr(a, b) else (1 if gr(b, a) else 0)))
            rval.append([rows[0]])
            for i in range(1, len(rows)):
                if eq(rows[i], rows[i - 1]):
                    rval[-1].append(rows[i])
                else:
                    rval.append([rows[i]])
        elif len(rows) == 1:
            rval.append([rows[0]])
        return rval
