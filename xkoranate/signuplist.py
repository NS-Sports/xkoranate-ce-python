import uuid

from .exceptions import XkorSearchFailedException
from .rng import Mt19937


class XkorSignupList:
    def __init__(self):
        self.ath = []
        self.min = 0.0
        self.max = 1.0
        self.r = Mt19937()

    def addAthlete(self, a):
        if a.id is None:
            a.id = self.generateID()
        self.ath.append(a)

    def adjustRank(self, rank):
        if self.max == self.min:
            # An unrankable field is evenly matched, not uniformly hopeless.
            # H2H paradigms only look at the difference, but the absolute
            # value reaches rand_kumaraswamy() for score-based sports, where
            # 0.0 would generate everyone's worst performance rather than an
            # average one.
            return 0.5
        return (rank - self.min) / (self.max - self.min)

    def athletes(self):
        return list(self.ath)

    def generateID(self):
        return uuid.UUID(int=self.r._r.getrandbits(128))

    def getAthleteByID(self, id):
        for i in self.ath:
            if i.id == id:
                return i
        raise XkorSearchFailedException(
            "Failed to find athlete with ID %s in XkorSignupList.getAthleteByID" % id)

    def maxRank(self):
        return self.max

    def minRank(self):
        return self.min

    def setAthletes(self, newAthletes):
        for i in newAthletes:
            if i.id is None:
                i.id = self.generateID()
        self.ath = newAthletes

    def setMaxRank(self, newMax):
        self.max = newMax

    def setMinRank(self, newMin):
        self.min = newMin
