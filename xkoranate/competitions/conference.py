"""Fixture scheduling for leagues split into conferences.

Each conference plays a round robin among its own teams, and every team
also plays every team in every other conference. Teams are referred to by
``(conference, index)`` so this module never needs to know about athletes;
the competition maps those back onto its start list.

Ported from the Google Apps Script prototype attached to issue #24
(``inter_conference.gs``), with three changes:

* conferences are paired off with the circle method, so each pair of
  conferences meets once per leg. The prototype listed every possible way
  of pairing the conferences, which repeats pairs once there are more than
  four of them;
* a smaller conference is padded with byes instead of wrapping around, so
  nobody ever plays twice on one matchday;
* cross-conference matchdays are spread evenly through the season instead of
  shuffled, so the same teams always produce the same schedule.
"""

from collections import namedtuple

# kind is "intra" (one conference playing among itself) or "inter" (two
# conferences playing each other); conferences holds one or two conference
# numbers; fixtures holds ((conference, index), (conference, index)) pairs,
# home team first
Section = namedtuple("Section", ["kind", "conferences", "fixtures"])


def _evenSize(n):
    return n + 1 if n & 1 else n


def conferencePairings(conferences):
    """Rounds pairing off the given conference numbers, circle method.

    Each pair of conferences meets exactly once. With an odd number of
    conferences one of them sits each round out. Within a pair the lower
    conference number comes first.
    """
    pool = list(conferences)
    if len(pool) < 2:
        return []
    if len(pool) & 1:
        pool.append(None)
    n = len(pool)
    rval = []
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = pool[i], pool[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((min(a, b), max(a, b)))
        rval.append(pairs)
        # keep the first entry fixed and rotate the rest
        pool.insert(1, pool.pop())
    return rval


def crossFixtures(x, y, sizes, round_, leg, pairingRound, width):
    """One round of conference x playing conference y.

    Team i of x meets team (i + round_) mod width of y, so over width rounds
    everyone meets everyone once and nobody plays twice in a round. Indices
    past a conference's size are byes. The whole of one conference is at home
    in a round; that alternates by round and flips each leg, so two legs give
    every pair one home game each.
    """
    xHome = (round_ + leg + pairingRound) % 2 == 0
    rval = []
    for i in range(width):
        j = (i + round_) % width
        if i >= sizes[x] or j >= sizes[y]:
            continue
        if xHome:
            rval.append(((x, i), (y, j)))
        else:
            rval.append(((y, j), (x, i)))
    return rval


def interleave(intraCount, crossCount):
    """Order intra (False) and cross (True) matchdays, cross spread evenly."""
    total = intraCount + crossCount
    rval = []
    for t in range(total):
        rval.append((t + 1) * crossCount // total > t * crossCount // total)
    return rval


def conferenceSchedule(sizes, ownLegs, otherLegs):
    """Every matchday of a conference league, as a list of lists of Sections.

    sizes is the number of teams in each conference. ownLegs is how many times
    teams meet within their conference, otherLegs how many times they meet
    each team in every other conference.
    """
    from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition

    sizes = list(sizes)
    ownLegs = max(0, ownLegs)
    otherLegs = max(0, otherLegs)
    largest = max(sizes) if sizes else 0

    # within conferences: the same fixtures a round robin of these groups
    # would play, so a single conference schedules exactly like one
    intraDays = []
    if largest >= 2 and ownLegs > 0:
        width = _evenSize(largest)
        for k in range(ownLegs * (width - 1)):
            fixtures = XkorRoundRobinCompetition.generateFixtures(k, width)
            sections = []
            for c, size in enumerate(sizes):
                pairs = [((c, h), (c, a)) for h, a in fixtures if h < size and a < size]
                if pairs:
                    sections.append(Section("intra", (c,), pairs))
            intraDays.append(sections)

    # across conferences: leg, then round, then which conferences meet, so
    # consecutive cross matchdays bring opponents from different conferences
    crossDays = []
    pairings = conferencePairings([c for c, size in enumerate(sizes) if size > 0])
    if pairings and otherLegs > 0:
        for leg in range(otherLegs):
            for r in range(largest):
                for p, pairs in enumerate(pairings):
                    sections = []
                    for x, y in pairs:
                        fixtures = crossFixtures(x, y, sizes, r, leg, p, largest)
                        if fixtures:
                            sections.append(Section("inter", (x, y), fixtures))
                    crossDays.append(sections)

    rval = []
    intraIter = iter(intraDays)
    crossIter = iter(crossDays)
    for isCross in interleave(len(intraDays), len(crossDays)):
        day = next(crossIter) if isCross else next(intraIter)
        if day:
            rval.append(day)
    return rval
