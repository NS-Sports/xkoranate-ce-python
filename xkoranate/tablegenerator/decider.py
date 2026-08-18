"""Parsing for the "(score NAME)" tiebreaker tags that
XkorAbstractH2HParadigm._formatScoreResults() appends to a simulated match's
printed output, e.g. "Aquilla 2–2 Busby (3–2 OT)" or, for a two-stage
tiebreaker, "Aquilla 2–2 Busby (2–2 AET) (4–3 pen.)". Sport files name these
tiebreakers freely — OT, SO, AET, pen., GG, ET, Sudden Death, + — so a match
is bucketed into the table's two decider categories ("OT" for extra
time/golden goal/replayed periods, "SO" for a shootout/penalties) by
keyword rather than by exact name.

Only known keywords count. A trailing "(2–1 Reserve)" is a perfectly ordinary
thing for a team name to end with, and nothing in the text distinguishes it
from a tiebreaker tag whose name we happen not to know — so an unrecognized
name is left alone as part of the team name rather than guessed at. This only
limits free-text entry (typed or copy-pasted results, and the <match> lines in
a saved table): a competition simulated in-app tags its own matches
structurally in XkorRoundRobinCompetition.scorinateMatchday(), never by
re-reading its printed output, so a sport file's custom tiebreaker name still
lands in the right bucket there.
"""

import re

from ..variant import toDouble

_TRAILING_DECIDER = re.compile(r"\s*\(([0-9]+)[-–:]([0-9]+)\s+([^()]+?)\)\s*$")

# the inline marker recognized directly after a score, e.g. "Aquilla 3–2 OT
# Busby". \b keeps a team name that merely starts with these letters — Ottawa,
# Southampton — from being read as a marker.
MATCH_RESULT_PATTERN = r"([0-9]+)[-–:]([0-9]+)(?:\s+(OT|SO)\b)?"

_MATCH_RESULT = re.compile(MATCH_RESULT_PATTERN)

_SHOOTOUT_KEYWORDS = frozenset((
    "so", "shootout", "shootouts", "pen", "pens", "pk", "pks", "penalty",
    "penalties",
))

_OVERTIME_KEYWORDS = frozenset((
    "ot", "aet", "et", "gg", "+", "extra time", "extratime", "overtime",
    "sudden death", "suddendeath", "golden goal", "goldengoal",
    "silver goal", "silvergoal",
))

# numbered overtime periods, e.g. "2OT", "OT3"
_NUMBERED_OVERTIME = re.compile(r"^(?:[0-9]+ ?ot|ot ?[0-9]+)$")


def classify(name):
    """Bucket a tiebreaker name as "OT" or "SO", or None if unrecognized."""
    normalized = " ".join(name.strip().lower().rstrip(".").split())
    if normalized in _SHOOTOUT_KEYWORDS:
        return "SO"
    if normalized in _OVERTIME_KEYWORDS or _NUMBERED_OVERTIME.match(normalized):
        return "OT"
    return None


def stripTrailingDeciders(text, baseScore1=None, baseScore2=None):
    """Peel every trailing "(score NAME)" block off the end of `text`.

    Returns (remainingText, score1, score2, decider). `decider` is the
    classification of the last (i.e. deciding) block, or None if `text` ended
    in no such block — in which case `remainingText == text` and score1/score2
    are also None, so the caller should keep its own base score/decider. A
    trailing block whose name isn't a recognized tiebreaker keyword isn't one
    of these tags as far as we can tell, so it's left in `remainingText` as
    part of the team name and stops any further peeling.

    When there IS a trailing block, score1/score2 are always concrete
    numbers:
      - if the deciding block is OT-type, its own (already-combined) score
        is used directly, matching how the simulator prints a running
        extra-time/golden-goal total;
      - if the deciding block is a shootout, the score one stage back (the
        previous OT-type block's score, or `baseScore1`/`baseScore2` if the
        shootout was the only stage) is used, nudged towards the shootout
        winner by nudgeForShootout().
    """
    blocks = []
    remainder = text
    while True:
        m = _TRAILING_DECIDER.search(remainder)
        if not m:
            break
        kind = classify(m.group(3))
        if kind is None:
            break
        blocks.insert(0, (toDouble(m.group(1)), toDouble(m.group(2)), kind))
        remainder = remainder[:m.start()]

    if not blocks:
        return (text, None, None, None)

    decider = blocks[-1][2]
    if decider == "OT":
        score1, score2 = blocks[-1][0], blocks[-1][1]
    else:  # "SO" — its own tally isn't a real score; find what preceded it
        if len(blocks) >= 2 and blocks[-2][2] == "OT":
            score1, score2 = blocks[-2][0], blocks[-2][1]
        else:
            score1, score2 = baseScore1, baseScore2
        score1, score2 = nudgeForShootout(score1, score2,
                                          blocks[-1][0], blocks[-1][1])

    return (remainder.rstrip(), score1, score2, decider)


def _qLeft(s, n):
    """QString::left(n): whole string if n < 0 or n > size."""
    if n < 0 or n > len(s):
        return s
    return s[:n]


def _qRight(s, n):
    """QString::right(n): whole string if n < 0 or n > size."""
    if n < 0 or n > len(s):
        return s
    return s[len(s) - n:] if n else ""


def parseMatchLine(text):
    """Parse one free-text match result into
    (homeTeam, awayTeam, score1, score2, decider), or None if `text` holds no
    score at all.

    Scores take the form "Aquilla 3–1 Busby", with an en dash, hyphen-minus or
    colon as the delimiter. A decider can be marked either inline after the
    score ("Aquilla 3–2 OT Busby") or, as the simulator prints it, as a
    trailing tag after the away team ("Aquilla 2–2 Busby (3–2 OT)").

    This is the one parser behind both the match-results text box and the
    <match> lines of a saved table, so the two can't drift apart.
    """
    m = _MATCH_RESULT.search(text)
    if m is None:
        return None

    index = m.start()
    matchedLength = m.end() - m.start()
    homeTeam = _qLeft(text, index - 1)
    awayTeam = _qRight(text, len(text) - index - matchedLength - 1)
    score1 = toDouble(m.group(1))
    score2 = toDouble(m.group(2))
    decider = m.group(3)

    awayTeam, taggedScore1, taggedScore2, taggedDecider = stripTrailingDeciders(
        awayTeam, score1, score2)
    if taggedDecider is not None:
        decider = taggedDecider
        score1, score2 = taggedScore1, taggedScore2

    return (homeTeam, awayTeam, score1, score2, decider)


def nudgeForShootout(score1, score2, soScore1, soScore2):
    """Break a tied (score1, score2) using the shootout tally, and return the
    adjusted pair.

    A shootout's own tally isn't a goal count and doesn't belong in the table,
    but a shootout always produces a winner, so a game it decided must not go
    into the standings as a draw. The winner is credited with one more goal,
    mirroring how a shootout-decided game's official final score is recorded
    (as in NHL/IIHF box scores). A pair that isn't tied already has a winner
    and is returned untouched.
    """
    if score1 is None or score1 != score2 or soScore1 == soScore2:
        return (score1, score2)
    if soScore1 > soScore2:
        return (score1 + 1, score2)
    return (score1, score2 + 1)
