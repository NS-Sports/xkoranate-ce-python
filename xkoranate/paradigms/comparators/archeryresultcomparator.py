from ...variant import toDouble
from .basicresultcomparator import XkorBasicResultComparator


class XkorArcheryResultComparator(XkorBasicResultComparator):
    def __init__(self, type, opt):
        super().__init__(type, opt)
        if type == "rankingRound":
            self.isRankingRound = True
        else:
            self.isRankingRound = False

    def __call__(self, a, b):
        if self.isAscending:
            return self.sortAscending(a, b)
        else:
            return self.sortAscending(b, a)

    def sortAscending(self, a, b):
        if a.score() < b.score():
            return True
        elif (self.isRankingRound and a.score() == b.score()
              and toDouble(a.value("tens")) < toDouble(b.value("tens"))):
            return True
        elif (self.isRankingRound and a.score() == b.score()
              and a.value("tens") == b.value("tens")
              and toDouble(a.value("Xs")) < toDouble(b.value("Xs"))):
            return True
        elif (a.score() == b.score()
              and (not self.isRankingRound
                   or (a.value("tens") == b.value("tens") and a.value("Xs") == b.value("Xs")))
              and toDouble(a.value("tbScore")) < toDouble(b.value("tbScore"))):
            return True
        elif (a.score() == b.score()
              and (not self.isRankingRound
                   or (a.value("tens") == b.value("tens") and a.value("Xs") == b.value("Xs")))
              and a.value("tbScore") == b.value("tbScore")
              and toDouble(a.value("lots")) < toDouble(b.value("lots"))):
            return True
        else:
            return False
