from ...variant import toDouble, toList, toString
from .basicresultcomparator import XkorBasicResultComparator


class XkorShootingResultComparator(XkorBasicResultComparator):
    def __init__(self, type, opt):
        super().__init__(type, opt)
        if type == "qualifying":
            self.isQualifying = True
        else:
            self.isQualifying = False
        if toString(opt.get("useBestGroups", "false")) == "true":
            self.useBestGroups = True
        else:
            self.useBestGroups = False

    def __call__(self, a, b):
        if self.isAscending:
            return self.sortAscending(a, b)
        else:
            return self.sortAscending(b, a)

    def sortAscending(self, a, b):
        if a.score() < b.score():
            return True
        elif self.isQualifying and self.useBestGroups and a.score() == b.score():
            # figure out who had the best last group
            aAttempts = toList(a.value("attempts"))
            bAttempts = toList(b.value("attempts"))
            i = 0
            while i < len(aAttempts) and i < len(bAttempts):
                if toDouble(aAttempts[len(aAttempts) - i - 1]) < toDouble(bAttempts[len(bAttempts) - i - 1]):
                    return True
                elif toDouble(aAttempts[len(aAttempts) - i - 1]) > toDouble(bAttempts[len(bAttempts) - i - 1]):
                    return False
                i += 1
        if a.score() == b.score():
            aShootoffScores = toList(a.value("shootoffScores"))
            bShootoffScores = toList(b.value("shootoffScores"))
            i = 0
            while i < len(aShootoffScores) and i < len(bShootoffScores):
                if toDouble(aShootoffScores[i]) < toDouble(bShootoffScores[i]):
                    return True
                elif toDouble(aShootoffScores[i]) > toDouble(bShootoffScores[i]):
                    return False
                i += 1
        return False
