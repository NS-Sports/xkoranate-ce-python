from ...variant import toDouble
from .basicresultcomparator import XkorBasicResultComparator


class XkorPointsRaceResultComparator(XkorBasicResultComparator):
    def __call__(self, a, b):
        if a.score() > b.score():
            return True
        elif a.score() == b.score() and toDouble(a.value("laps")) > toDouble(b.value("laps")):
            return True
        elif (a.score() == b.score() and a.value("laps") == b.value("laps")
              and toDouble(a.value("time")) > toDouble(b.value("time"))):
            return True
        else:
            return False
