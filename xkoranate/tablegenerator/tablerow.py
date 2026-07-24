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

    def draws(self):
        return self.scores.get("_draws", 0.0)

    def goalsAgainst(self):
        return self.scores.get("_goalsAgainst", 0.0)

    def goalDifference(self):
        return self.scores.get("_goalDifference", 0.0)

    def goalsFor(self):
        return self.scores.get("_goalsFor", 0.0)

    def h2hAwayGoals(self, teams):
        rval = 0
        for i in teams:
            teamResults = self.h2hResults.get(i, [])
            for j in teamResults:
                if j.team2 == self.n:  # if this team was away
                    rval += j.goalsFor(self.n)
        return rval

    def h2hGoalDifference(self, teams):
        rval = 0
        for i in teams:
            teamResults = self.h2hResults.get(i, [])
            for j in teamResults:
                rval += j.goalDifference(self.n)
        return rval

    def h2hGoalsAgainst(self, teams):
        rval = 0
        for i in teams:
            teamResults = self.h2hResults.get(i, [])
            for j in teamResults:
                rval += j.goalsAgainst(self.n)
        return rval

    def h2hGoalsFor(self, teams):
        rval = 0
        for i in teams:
            teamResults = self.h2hResults.get(i, [])
            for j in teamResults:
                rval += j.goalsFor(self.n)
        return rval

    def h2hPoints(self, teams):
        rval = 0
        for i in teams:
            teamResults = self.h2hResults.get(i, [])
            for j in teamResults:
                rval += j.points(self.n)
        return rval

    def h2hWins(self, teams):
        rval = 0
        for i in teams:
            teamResults = self.h2hResults.get(i, [])
            for j in teamResults:
                rval += 1 if j.points(self.n) == 3 else 0
        return rval

    def insertMatch(self, t2name, t1score, t2score, home, decider=None):
        if home:
            self.h2hResults.setdefault(t2name, []).insert(
                0, XkorTableMatch(self.n, t2name, t1score, t2score, decider))
        else:
            self.h2hResults.setdefault(t2name, []).insert(
                0, XkorTableMatch(t2name, self.n, t2score, t1score, decider))
            self.scores["_awayGoals"] = self.scores.get("_awayGoals", 0.0) + t1score
        self.scores["_played"] = self.scores.get("_played", 0.0) + 1
        if t1score > t2score:
            self.scores["_wins"] = self.scores.get("_wins", 0.0) + 1
            if decider == "OT":
                self.scores["_otWins"] = self.scores.get("_otWins", 0.0) + 1
            elif decider == "SO":
                self.scores["_soWins"] = self.scores.get("_soWins", 0.0) + 1
        elif t1score == t2score:
            self.scores["_draws"] = self.scores.get("_draws", 0.0) + 1
        else:
            self.scores["_losses"] = self.scores.get("_losses", 0.0) + 1
            if decider == "OT":
                self.scores["_otLosses"] = self.scores.get("_otLosses", 0.0) + 1
            elif decider == "SO":
                self.scores["_soLosses"] = self.scores.get("_soLosses", 0.0) + 1
        self.scores["_goalsFor"] = self.scores.get("_goalsFor", 0.0) + t1score
        self.scores["_goalsAgainst"] = self.scores.get("_goalsAgainst", 0.0) + t2score
        self.scores["_goalDifference"] = self.scores.get("_goalDifference", 0.0) + t1score - t2score

    def losses(self):
        return self.scores.get("_losses", 0.0)

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
