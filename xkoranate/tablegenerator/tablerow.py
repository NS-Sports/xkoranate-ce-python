from .tablematch import XkorTableMatch


class XkorTableRow:
    def __init__(self, name=""):
        self.n = name  # name
        self.scores = {}  # QHash<QString, double>
        # QMultiHash<QString, XkorTableMatch>; Qt's values() returns the
        # most-recently-inserted value first, so insert at the front
        self.h2hResults = {}

    def clone(self):
        rval = XkorTableRow(self.n)
        rval.scores = dict(self.scores)
        rval.h2hResults = {k: list(v) for k, v in self.h2hResults.items()}
        return rval

    def awayGoals(self):
        return self.scores.get("_awayGoals", 0.0)

    def awayWins(self):
        return self.scores.get("_awayWins", 0.0)

    def draws(self):
        return self.scores.get("_draws", 0.0)

    def goalsAgainst(self):
        return self.scores.get("_goalsAgainst", 0.0)

    def homeGoalsAgainst(self):
        return self.scores.get("_homeGoalsAgainst", 0.0)

    def homeLosses(self):
        return self.scores.get("_homeLosses", 0.0)

    def goalDifference(self):
        return self.scores.get("_goalDifference", 0.0)

    def goalsFor(self):
        return self.scores.get("_goalsFor", 0.0)

    def _h2hSum(self, teams, value):
        """value(match) summed over this team's games against `teams`."""
        rval = 0
        for i in teams:
            for j in self.h2hResults.get(i, []):
                rval += value(j)
        return rval

    def h2hAwayGoals(self, teams):
        # only the games this team played away
        return self._h2hSum(teams, lambda j: j.goalsFor(self.n) if j.team2 == self.n else 0)

    def h2hGoalDifference(self, teams):
        return self._h2hSum(teams, lambda j: j.goalDifference(self.n))

    def h2hGoalsAgainst(self, teams):
        return self._h2hSum(teams, lambda j: j.goalsAgainst(self.n))

    def h2hGoalsFor(self, teams):
        return self._h2hSum(teams, lambda j: j.goalsFor(self.n))

    def h2hPoints(self, teams):
        return self._h2hSum(teams, lambda j: j.points(self.n))

    def h2hWins(self, teams):
        return self._h2hSum(teams, lambda j: 1 if j.points(self.n) == 3 else 0)

    def _bump(self, key, n=1):
        self.scores[key] = self.scores.get(key, 0.0) + n

    def insertMatch(self, t2name, t1score, t2score, home, decider=None, cross=False):
        if home:
            self.h2hResults.setdefault(t2name, []).insert(
                0, XkorTableMatch(self.n, t2name, t1score, t2score, decider))
        else:
            self.h2hResults.setdefault(t2name, []).insert(
                0, XkorTableMatch(t2name, self.n, t2score, t1score, decider))
            self._bump("_awayGoals", t1score)
        self._bump("_played")
        if t1score > t2score:
            self._bump("_wins")
            if not home:
                self._bump("_awayWins")
            if decider == "OT":
                self._bump("_otWins")
            elif decider == "SO":
                self._bump("_soWins")
        elif t1score == t2score:
            self._bump("_draws")
        else:
            self._bump("_losses")
            if home:
                self._bump("_homeLosses")
            if decider == "OT":
                self._bump("_otLosses")
            elif decider == "SO":
                self._bump("_soLosses")
        if cross:
            # a game against another conference; the table may score these
            # differently (see XkorTable.setCrossPoints)
            if t1score == t2score:
                key = "_crossDraws"
            else:
                key = "_cross" + (decider or "") + ("Wins" if t1score > t2score else "Losses")
            self._bump(key)
        self._bump("_goalsFor", t1score)
        self._bump("_goalsAgainst", t2score)
        if home:
            self._bump("_homeGoalsAgainst", t2score)
        self.scores["_goalDifference"] = self.scores.get("_goalDifference", 0.0) + t1score - t2score

    def losses(self):
        return self.scores.get("_losses", 0.0)

    def crossWins(self):
        """Regulation wins against another conference."""
        return self.scores.get("_crossWins", 0.0)

    def crossDraws(self):
        return self.scores.get("_crossDraws", 0.0)

    def crossLosses(self):
        """Regulation losses against another conference."""
        return self.scores.get("_crossLosses", 0.0)

    def crossDecided(self, decider, won):
        """OT or SO wins/losses against another conference."""
        return self.scores.get("_cross" + decider + ("Wins" if won else "Losses"), 0.0)

    def name(self):
        return self.n

    def otLosses(self):
        return self.scores.get("_otLosses", 0.0)

    def otWins(self):
        return self.scores.get("_otWins", 0.0)

    def played(self):
        return self.scores.get("_played", 0.0)

    def regulationLosses(self):
        return self.losses() - self.otLosses() - self.soLosses()

    def regulationWins(self):
        return self.wins() - self.otWins() - self.soWins()

    def soLosses(self):
        return self.scores.get("_soLosses", 0.0)

    def soWins(self):
        return self.scores.get("_soWins", 0.0)

    def result(self, opponent):
        rval = (-1, -1)
        teamResults = self.h2hResults.get(opponent, [])
        for i in teamResults:
            if i.team1 == self.n and i.team2 == opponent:
                rval = (i.score1, i.score2)
        return rval

    def setValue(self, columnName, value):
        self.scores[columnName] = value

    def value(self, columnName):
        return self.scores.get(columnName, 0.0)

    def wins(self):
        return self.scores.get("_wins", 0.0)
