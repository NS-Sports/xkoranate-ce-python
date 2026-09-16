"""Played-match storage and matchday ordering for a knockout bracket.

Two things XkorSingleEliminationCompetition used to carry inline:

BracketRows is the pipe-delimited codec for played matches, which live in
the resume options as a flat list of strings.

MatchdaySchedule is the mapping between matchdays (what the user picks in
the scorinate dropdown) and bracket rounds. They differ only because an
optional third-place playoff is played before the final, but that one
offset used to be re-derived from `rounds - 1` / `rounds - 2` arithmetic in
five separate places, which is where the next off-by-one would have landed.
Building the running order once and indexing into it keeps them in step.
"""

from ..variant import qNumber, toDouble, toInt

FIELD_SEP = "|"
THIRD_PLACE_ROUND = "3P"  # sentinel round marker for the third-place playoff


class BracketRows:
    """The played matches of a bracket, as stored in the resume options."""

    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def append(self, row):
        self.rows.append(row)

    @staticmethod
    def make(round_, match, home, away, score1, score2, decider, winner):
        return FIELD_SEP.join([
            str(round_), str(match),
            str(home.id) if home is not None else "",
            str(away.id) if away is not None else "",
            qNumber(score1) if score1 is not None else "",
            qNumber(score2) if score2 is not None else "",
            decider or "",
            str(winner.id) if winner is not None else "",
        ])

    @staticmethod
    def parse(row):
        f = row.split(FIELD_SEP)
        if len(f) < 8:
            return None
        return {
            "round": f[0], "match": toInt(f[1]),
            "home": f[2], "away": f[3],
            "score1": toDouble(f[4]) if f[4] else None,
            "score2": toDouble(f[5]) if f[5] else None,
            "decider": f[6], "winner": f[7],
        }

    def dropRound(self, round_):
        """Forget a round's results, so scorinating it again replaces them."""
        self.rows = [row for row in self.rows
                     if (self.parse(row) or {}).get("round") != str(round_)]

    def forRound(self, round_):
        """{match index: parsed row} for one round."""
        rval = {}
        for row in self.rows:
            r = self.parse(row)
            if r is not None and r["round"] == str(round_):
                rval[r["match"]] = r
        return rval

    def winners(self, round_, expected, resolve):
        """Winners of every match in a round, or None if it isn't complete."""
        rows = self.forRound(round_)
        if len(rows) < expected:
            return None
        rval = []
        for m in range(expected):
            if m not in rows:
                return None
            rval.append(resolve(rows[m]["winner"]))
        return rval

    def losers(self, round_, resolve):
        rval = []
        rows = self.forRound(round_)
        for m in sorted(rows):
            row = rows[m]
            loser = row["away"] if row["winner"] == row["home"] else row["home"]
            athlete = resolve(loser)
            if athlete is not None:
                rval.append(athlete)
        return rval


class MatchdaySchedule:
    """The running order of a bracket, one entry per matchday.

    Each entry is (bracket round, is the third-place playoff). The playoff
    sits immediately before the final, which is the whole reason matchdays
    and rounds aren't the same number.
    """

    def __init__(self, rounds, thirdPlace):
        self.rounds = rounds
        self.thirdPlace = thirdPlace and rounds >= 2
        self.order = []
        for r in range(rounds):
            if self.thirdPlace and r == rounds - 1:
                # contested by the losers of the semi-finals, played first
                self.order.append((rounds - 2, True))
            self.order.append((r, False))

    def __len__(self):
        return len(self.order)

    def roundForMatchday(self, matchday):
        """(bracket round, is the playoff) for a matchday index."""
        if 0 <= matchday < len(self.order):
            return self.order[matchday]
        # out of range: name the last round rather than raising, as the
        # arithmetic this replaces did
        return (max(self.rounds - 1, 0), False)

    def matchdayForRound(self, round_):
        """Inverse, for real bracket rounds."""
        for md, (r, isThirdPlace) in enumerate(self.order):
            if r == round_ and not isThirdPlace:
                return md
        return round_

    def thirdPlaceMatchday(self):
        """Where the playoff is played, or one past the end if there isn't one."""
        for md, (_, isThirdPlace) in enumerate(self.order):
            if isThirdPlace:
                return md
        return self.rounds

    def matchesBefore(self, matchday, matchesInRound):
        """How many matches the whole bracket plays before this matchday.

        The single place the playoff's position shifts the numbering, so
        every match number — bracket rounds and the playoff alike — comes
        out of the same running total.
        """
        return sum(1 if isThirdPlace else matchesInRound(r)
                   for r, isThirdPlace in self.order[:matchday])
