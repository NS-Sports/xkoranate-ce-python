import math
import sys

from ...variant import toDouble, toList
from .basicresultcomparator import XkorBasicResultComparator


class XkorTimedResultComparator(XkorBasicResultComparator):
    def __init__(self, type, opt):
        super().__init__(type, opt)
        if type == "noTiebreakers":
            self.useTiebreakers = False
        else:
            self.useTiebreakers = True

        if "interheatTiebreakerDigits" in opt:
            self.useRounding = True
            self.roundingValue = math.pow(10.0, -toDouble(opt.get("interheatTiebreakerDigits")))
        else:
            self.useRounding = False
            self.roundingValue = 0.0

    def __call__(self, a, b):
        if self.isAscending:
            return self.sortAscending(a, b)
        else:
            return self.sortAscending(b, a)

    @staticmethod
    def compareVariant(a, b):
        return toDouble(a) < toDouble(b)

    @staticmethod
    def compareVariantDescending(a, b):
        return toDouble(b) < toDouble(a)

    def roundScore(self, score, rounding):
        if score == sys.float_info.max or score == -sys.float_info.max:
            return score
        else:
            return int(score / rounding) * rounding

    def sortAscending(self, a, b):
        roundingApplies = self.useRounding and a.value("heat") != b.value("heat")
        if not roundingApplies and a.score() - b.score() < -0.0000000001:
            # a.score() < b.score() — we have to use this ridiculous form due to rounding issues
            return True
        elif roundingApplies and (self.roundScore(a.score(), self.roundingValue)
                                  < self.roundScore(b.score(), self.roundingValue)):
            return True
        elif not roundingApplies and a.score() - b.score() > 0.0000000001:  # a.score() > b.score()
            return False
        elif roundingApplies and (self.roundScore(a.score(), self.roundingValue)
                                  > self.roundScore(b.score(), self.roundingValue)):
            return False
        elif self.useTiebreakers and "attempts" in a.result:
            attemptsA = toList(a.value("attempts"))
            attemptsB = toList(b.value("attempts"))

            if len(attemptsA) < len(attemptsB):
                # having more attempts is always better regardless of what order the numbers go
                return not self.isAscending
            elif len(attemptsA) > len(attemptsB):
                return self.isAscending

            if self.isAscending:
                attemptsA.sort(key=toDouble)
                attemptsB.sort(key=toDouble)
            else:
                attemptsA.sort(key=toDouble, reverse=True)
                attemptsB.sort(key=toDouble, reverse=True)
            i = 0
            while i < len(attemptsA) and i < len(attemptsB):
                if not roundingApplies and toDouble(attemptsA[i]) - toDouble(attemptsB[i]) < -0.0000000001:
                    return True
                elif roundingApplies and (self.roundScore(toDouble(attemptsA[i]), self.roundingValue)
                                          < self.roundScore(toDouble(attemptsB[i]), self.roundingValue)):
                    return True
                if not roundingApplies and toDouble(attemptsA[i]) - toDouble(attemptsB[i]) > 0.0000000001:
                    return False
                elif roundingApplies and (self.roundScore(toDouble(attemptsA[i]), self.roundingValue)
                                          > self.roundScore(toDouble(attemptsB[i]), self.roundingValue)):
                    return False
                i += 1
            return False
        else:
            return False
