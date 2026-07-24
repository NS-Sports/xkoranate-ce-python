class XkorTableMatch:
    def __init__(self, t1, t2, s1, s2, decider=None):
        self.team1 = t1
        self.team2 = t2
        self.score1 = s1
        self.score2 = s2
        # None for a match decided in regulation; "OT" for one decided in
        # overtime/extra time; "SO" for one decided by shootout/penalties
        self.decider = decider

    def goalDifference(self, team):
        rval = 0
        if team == self.team1:
            rval = self.score1 - self.score2
        elif team == self.team2:
            rval = self.score2 - self.score1
        return rval

    def goalsAgainst(self, team):
        rval = 0
        if team == self.team1:
            rval = self.score2
        elif team == self.team2:
            rval = self.score1
        return rval

    def goalsFor(self, team):
        rval = 0
        if team == self.team1:
            rval = self.score1
        elif team == self.team2:
            rval = self.score2
        return rval

    def opponent(self, team):
        rval = ""
        if team == self.team1:
            rval = self.team2
        elif team == self.team2:
            rval = self.team1
        return rval

    def points(self, team):
        rval = 0
        if team == self.team1:
            if self.score1 > self.score2:
                rval = 3
            elif self.score1 == self.score2:
                rval = 1
        elif team == self.team2:
            if self.score2 > self.score1:
                rval = 3
            elif self.score1 == self.score2:
                rval = 1
        return rval
