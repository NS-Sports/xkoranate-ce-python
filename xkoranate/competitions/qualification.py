"""Qualification markers for standings: Q for a team that has mathematically
qualified, E for one that has been eliminated.

Pure logic, no Qt. A competition describes each of its groups as a
`QualificationGroup` and gets back, per group, a dict of team -> "Q"/"E";
teams whose fate is still open are simply left out.

Three rules are supported (see `QualificationSettings`):

* top X — the top X of a single table
* top X in each group
* top X in each group plus the best N teams placed X+1 across the groups

"Mathematically" is meant strictly: a marker only appears once no
combination of the remaining results can change it. Only the table's first
sort criterion (points, wins or a win percentage) can be projected forward;
the tiebreakers below it depend on scores nobody knows yet, so a tie on that
first criterion is always counted against the team being judged. That makes
the markers conservative — one can appear a matchday later than a person
working out head-to-heads by hand would call it — but never wrong. Once a
group is complete its real order (tiebreakers and all) is used instead.
"""

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field, replace
from fractions import Fraction

from xkoranate.variant import toInt, toString

MODE_OFF = "off"
MODE_TOP = "top"
MODE_TOP_PLUS_BEST = "topPlusBest"

QUALIFIED = "Q"
ELIMINATED = "E"

# the most distinct final standings worth enumerating for one group; past
# this the remaining results are judged team by team instead (see
# _boundsAnalysis), which is still sound, just slower to call a clinch
SCENARIO_CAP = 20000


@dataclass(frozen=True)
class QualificationSettings:
    mode: str = MODE_OFF
    places: int = 2  # X
    bestOf: int = 1  # N, only used by MODE_TOP_PLUS_BEST

    @classmethod
    def fromOptions(cls, opts):
        mode = toString(opts.get("qualificationMode", MODE_OFF)) or MODE_OFF
        if mode not in (MODE_OFF, MODE_TOP, MODE_TOP_PLUS_BEST):
            mode = MODE_OFF
        places = toInt(opts.get("qualificationPlaces", 2)) if "qualificationPlaces" in opts else 2
        bestOf = toInt(opts.get("qualificationBestOf", 1)) if "qualificationBestOf" in opts else 1
        return cls(mode, max(1, places), max(1, bestOf))

    def toOptions(self):
        return {"qualificationMode": self.mode,
                "qualificationPlaces": str(self.places),
                "qualificationBestOf": str(self.bestOf)}

    def isEnabled(self):
        return self.mode != MODE_OFF and self.places >= 1

    def forGroupCount(self, groupCount):
        """The rule as it applies to an event with this many groups: "best N
        next-placed" needs other groups to compare against."""
        if self.mode == MODE_TOP_PLUS_BEST and (groupCount < 2 or self.bestOf < 1):
            return replace(self, mode=MODE_TOP)
        return self


def ordinal(n):
    if n % 100 in (11, 12, 13):
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


@dataclass
class QualificationGroup:
    """One group (or heat) as the engine sees it.

    teams      every entrant that can still be placed
    current    metric earned so far (teams missing count as 0); None when
               the table's first sort criterion can't be projected forward
    remaining  fixtures still to play, as (home, away) team pairs
    outcomes   what each side of one match can add to its metric, as
               (home, away) pairs; None when the metric is unknown
    order      final standings as tie bins (best first) — only read once
               the group is complete
    scale      multiplies the metric before it's compared with another
               group's (1 / games played for a win percentage)
    excluded   entrants who can't be ranked at all (DNF, DSQ): always E
    """
    teams: list
    current: dict = None
    remaining: list = field(default_factory=list)
    outcomes: list = None
    order: list = None
    scale: Fraction = Fraction(1)
    excluded: list = field(default_factory=list)

    def isComplete(self):
        return not self.remaining

    def metricKnown(self):
        return self.current is not None and (self.isComplete() or self.outcomes is not None)


@dataclass
class _TeamOutlook:
    maxWorst: int  # the lowest place the team can end up in, ties lost
    minBest: int  # the highest place it can reach, ties won
    lowAtNext: Fraction = None  # its smallest value in any finish that can be X+1 at worst
    highAtNext: Fraction = None  # its largest value in any finish that can be X+1 at best


@dataclass
class _GroupAnalysis:
    outlook: dict = None  # team -> _TeamOutlook, for incomplete groups
    nextRange: tuple = None  # (low, high) of the (X+1)th-placed value, scaled; None = unknown
    hasNext: bool = False  # whether the group has an (X+1)th place at all
    positions: dict = None  # team -> (first, last) place of its tie bin, for complete groups
    nextTeam: object = None  # the team shown (X+1)th, for complete groups


def leagueMarkers(groups, settings, crossRank=None):
    """team -> "Q"/"E" for each group.

    crossRank, when given, ranks the (X+1)th-placed teams of complete groups
    against each other exactly: it takes a list of (groupIndex, team) and
    returns them as tie bins, best first, or None when it can't.
    """
    settings = settings.forGroupCount(len(groups))
    if not settings.isEnabled():
        return [{} for _ in groups]

    places = settings.places
    analyses = [_analyse(g, places) for g in groups]

    if settings.mode == MODE_TOP:
        return [_topMarkers(g, a, places) for g, a in zip(groups, analyses)]

    exact = None
    if crossRank is not None and all(g.isComplete() for g in groups):
        exact = _exactNextPlaced(groups, analyses, settings.bestOf, crossRank)

    rval = []
    for groupNo, (g, a) in enumerate(zip(groups, analyses)):
        rivals = [other.nextRange if other.nextRange is not None else (None, None)
                  for otherNo, other in enumerate(analyses)
                  if otherNo != groupNo and other.hasNext]
        rval.append(_bestOfMarkers(g, a, places, settings.bestOf, rivals,
                                   None if exact is None else exact.get(groupNo)))
    return rval


def _topMarkers(group, analysis, places):
    rval = {t: ELIMINATED for t in group.excluded}
    if group.isComplete():
        for team, (first, last) in (analysis.positions or {}).items():
            if last <= places:
                rval[team] = QUALIFIED
            elif first > places:
                rval[team] = ELIMINATED
        return rval
    for team, o in (analysis.outlook or {}).items():
        if o.maxWorst <= places:
            rval[team] = QUALIFIED
        elif o.minBest > places:
            rval[team] = ELIMINATED
    return rval


def _bestOfMarkers(group, analysis, places, bestOf, rivals, exact):
    """rivals: the (low, high) (X+1)th-placed value of every other group
    that has an (X+1)th place; None for a bound that isn't known."""

    def couldFinishAtLeast(value):  # other groups whose X+1 might match or beat value
        return sum(1 for low, high in rivals if high is None or value is None or high >= value)

    def finishesAbove(value):  # other groups whose X+1 is certain to beat value
        return sum(1 for low, high in rivals if low is not None and value is not None and low > value)

    rval = {t: ELIMINATED for t in group.excluded}
    nextPlace = places + 1

    if group.isComplete():
        for team, (first, last) in (analysis.positions or {}).items():
            if last <= places:
                rval[team] = QUALIFIED
            elif first > nextPlace:
                rval[team] = ELIMINATED
            elif first == last == nextPlace:
                if exact is not None:
                    if exact != "":
                        rval[team] = exact
                    continue
                value = _scaledValue(group, team)
                if value is None:
                    continue
                if couldFinishAtLeast(value) < bestOf:
                    rval[team] = QUALIFIED
                elif finishesAbove(value) >= bestOf:
                    rval[team] = ELIMINATED
            # a tie straddling a cut-off is left open
        return rval

    for team, o in (analysis.outlook or {}).items():
        if o.maxWorst <= places or (
                o.maxWorst == nextPlace and couldFinishAtLeast(o.lowAtNext) < bestOf):
            rval[team] = QUALIFIED
        elif o.minBest > nextPlace or (
                o.minBest == nextPlace and finishesAbove(o.highAtNext) >= bestOf):
            rval[team] = ELIMINATED
    return rval


def _exactNextPlaced(groups, analyses, bestOf, crossRank):
    """groupIndex -> "Q"/"E"/"" for the team placed X+1 in each group, once
    every group is complete; None if the ranking can't be done."""
    candidates = [(groupNo, a.nextTeam) for groupNo, a in enumerate(analyses)
                  if a.hasNext and a.nextTeam is not None]
    if not candidates:
        return {}
    bins = crossRank(candidates)
    if bins is None:
        return None
    rval = {}
    first = 1
    for b in bins:
        last = first + len(b) - 1
        verdict = QUALIFIED if last <= bestOf else (ELIMINATED if first > bestOf else "")
        for groupNo, _team in b:
            rval[groupNo] = verdict
        first = last + 1
    return rval


def _scaledValue(group, team):
    if group.current is None:
        return None
    return Fraction(group.current.get(team, 0)) * group.scale


def _analyse(group, places):
    a = _GroupAnalysis()
    rankable = [t for t in group.teams if t not in group.excluded]
    a.hasNext = len(rankable) > places

    if group.isComplete():
        a.positions = {}
        flat = []
        first = 1
        for b in group.order or []:
            b = [t for t in b if t not in group.excluded]
            if not b:
                continue
            last = first + len(b) - 1
            for t in b:
                a.positions[t] = (first, last)
            flat.extend(b)
            first = last + 1
        if len(flat) > places:
            a.nextTeam = flat[places]
            value = _scaledValue(group, a.nextTeam)
            if value is not None:
                a.nextRange = (value, value)
        return a

    if not group.metricKnown():
        return a  # nothing can be said about an incomplete group

    a.outlook, nextRange = _scenarioAnalysis(group, rankable, places)
    if a.outlook is None:
        a.outlook, nextRange = _boundsAnalysis(group, rankable, places)
    if nextRange is not None:
        a.nextRange = (nextRange[0] * group.scale, nextRange[1] * group.scale)
    return a


def _integerise(group, teams):
    """The metric as integers over a common denominator, so the enumeration
    below hashes and compares plain ints rather than Fractions."""
    values = [Fraction(group.current.get(t, 0)) for t in teams]
    deltas = [(Fraction(h), Fraction(w)) for h, w in group.outcomes]
    denominator = 1
    for v in values + [x for pair in deltas for x in pair]:
        denominator = denominator * v.denominator // math.gcd(denominator, v.denominator)
    start = tuple(int(v * denominator) for v in values)
    outcomes = sorted({(int(h * denominator), int(w * denominator)) for h, w in deltas})
    return start, outcomes, denominator


def _scenarioAnalysis(group, teams, places):
    """Every reachable final standing, enumerated; (None, None) if there are
    too many."""
    n = len(teams)
    index = {t: i for i, t in enumerate(teams)}
    start, outcomes, denominator = _integerise(group, teams)

    states = {start}
    for home, away in group.remaining:
        i, j = index.get(home), index.get(away)
        if i is None or j is None:
            continue
        following = set()
        for s in states:
            for dh, da in outcomes:
                t = list(s)
                t[i] += dh
                t[j] += da
                following.add(tuple(t))
        if len(following) > SCENARIO_CAP:
            return None, None
        states = following

    maxWorst = [0] * n
    minBest = [n + 1] * n
    lowAtNext = [None] * n
    highAtNext = [None] * n
    nextLow = nextHigh = None
    nextPlace = places + 1
    for s in states:
        ordered = sorted(s)
        for i, v in enumerate(s):
            worst = n - bisect_left(ordered, v)  # 1 + others level or ahead
            best = n - bisect_right(ordered, v) + 1  # 1 + others strictly ahead
            if worst > maxWorst[i]:
                maxWorst[i] = worst
            if best < minBest[i]:
                minBest[i] = best
            if worst == nextPlace and (lowAtNext[i] is None or v < lowAtNext[i]):
                lowAtNext[i] = v
            if best == nextPlace and (highAtNext[i] is None or v > highAtNext[i]):
                highAtNext[i] = v
        if n > places:
            v = ordered[n - 1 - places]
            nextLow = v if nextLow is None else min(nextLow, v)
            nextHigh = v if nextHigh is None else max(nextHigh, v)

    def frac(v):
        return None if v is None else Fraction(v, denominator) * group.scale

    outlook = {t: _TeamOutlook(maxWorst[i], minBest[i], frac(lowAtNext[i]), frac(highAtNext[i]))
               for i, t in enumerate(teams)}
    nextRange = None if nextLow is None else (Fraction(nextLow, denominator), Fraction(nextHigh, denominator))
    return outlook, nextRange


def _boundsAnalysis(group, teams, places):
    """Each team on its own: the fewest and most it can still finish with.
    Treats every rival as free to hit either extreme at once, which overstates
    what's possible (two rivals can't both win their match against each
    other), so it calls a clinch later than enumeration would — never wrongly."""
    games = {t: 0 for t in teams}
    for home, away in group.remaining:
        if home in games:
            games[home] += 1
        if away in games:
            games[away] += 1
    gains = [Fraction(x) for pair in group.outcomes for x in pair] or [Fraction(0)]
    most, fewest = max(gains), min(gains)

    low = {t: Fraction(group.current.get(t, 0)) + games[t] * fewest for t in teams}
    high = {t: Fraction(group.current.get(t, 0)) + games[t] * most for t in teams}

    outlook = {}
    for t in teams:
        others = [o for o in teams if o != t]
        worst = 1 + sum(1 for o in others if high[o] >= low[t])
        best = 1 + sum(1 for o in others if low[o] > high[t])
        outlook[t] = _TeamOutlook(worst, best, low[t] * group.scale, high[t] * group.scale)

    nextRange = None
    if len(teams) > places:
        lows = sorted(low.values(), reverse=True)
        highs = sorted(high.values(), reverse=True)
        nextRange = (lows[places], highs[places])
    return outlook, nextRange


# --- ranked lists (mass start heats) -----------------------------------------

def parseRankToken(token):
    """A rank cell as rankedListOutput() writes it: a number, blank for a tie
    with the line above, or an em dash for an unrankable result."""
    token = token.strip()
    if token == "":
        return ""
    if token == "—":
        return "—"
    if token.isdigit():
        return int(token)
    return None
