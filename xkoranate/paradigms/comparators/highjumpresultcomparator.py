from ...variant import toInt
from .basicresultcomparator import XkorBasicResultComparator


class XkorHighJumpResultComparator(XkorBasicResultComparator):
    def __call__(self, a, b):
        if self.isAscending:
            return self.sortAscending(a, b)
        else:
            return self.sortAscending(b, a)

    def sortAscending(self, a, b):
        if a.score() < b.score():
            return True
        elif (a.score() == b.score()
              and toInt(a.value("lastHeightFailures")) > toInt(b.value("lastHeightFailures"))):
            return True
        elif (a.score() == b.score()
              and a.value("lastHeightFailures") == b.value("lastHeightFailures")
              and toInt(a.value("failures")) > toInt(b.value("failures"))):
            return True
        else:
            return False
