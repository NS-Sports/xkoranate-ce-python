class XkorTableMatch:
    def __init__(self, t1, t2, s1, s2, decider=None):
        self.team1 = t1
        self.team2 = t2
        self.score1 = s1
        self.score2 = s2
        # None for a match decided in regulation; "OT" for one decided in
        # overtime/extra time; "SO" for one decided by shootout/penalties
        self.decider = decider

    def _scores(self, team):
        """(team's score, its opponent's), or None if it didn't play."""
        if team == self.team1:
            return (self.score1, self.score2)
        if team == self.team2:
            return (self.score2, self.score1)
        return None

    def goalDifference(self, team):
        s = self._scores(team)
        return 0 if s is None else s[0] - s[1]

    def goalsAgainst(self, team):
        s = self._scores(team)
        return 0 if s is None else s[1]

    def goalsFor(self, team):
        s = self._scores(team)
        return 0 if s is None else s[0]

    def opponent(self, team):
        rval = ""
        if team == self.team1:
            rval = self.team2
        elif team == self.team2:
            rval = self.team1
        return rval

    def points(self, team):
        s = self._scores(team)
        if s is None:
            return 0
        if s[0] > s[1]:
            return 3
        return 1 if s[0] == s[1] else 0
