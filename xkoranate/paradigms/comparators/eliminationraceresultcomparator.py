from ...variant import toInt
from .basicresultcomparator import XkorBasicResultComparator


class XkorEliminationRaceResultComparator(XkorBasicResultComparator):
    def __call__(self, a, b):
        if a.contains("eliminationOrder") and not b.contains("eliminationOrder"):
            return False
        elif not a.contains("eliminationOrder") and b.contains("eliminationOrder"):
            return True
        elif a.contains("eliminationOrder") and b.contains("eliminationOrder"):
            return toInt(a.value("eliminationOrder")) > toInt(b.value("eliminationOrder"))
        elif a.contains("points") and not b.contains("points"):
            return True
        elif not a.contains("points") and b.contains("points"):
            return False
        elif (a.contains("points") and b.contains("points")
              and toInt(a.value("points")) != toInt(b.value("points"))):
            return toInt(a.value("points")) > toInt(b.value("points"))
        else:
            return a.score() < b.score()
