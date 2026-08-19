from ...variant import toDouble, toString
from .basicresultcomparator import XkorBasicResultComparator


class XkorH2HResultComparator(XkorBasicResultComparator):
    def __init__(self, type, opt):
        super().__init__(type, opt)
        self.tb = self.readOptionList(opt, "tiebreakerNames")

    def __call__(self, a, b):
        if self.isAscending:
            return self.sortAscending(a, b)
        else:
            return self.sortAscending(b, a)

    def sortAscending(self, a, b):
        if a.score() < b.score():
            return True
        elif a.score() == b.score() and "decision" in b.result:
            return True
        elif a.score() == b.score() and "decision" in a.result:
            return False
        elif a.score() == b.score():
            for i in self.tb:
                key = toString(i)
                if a.value(key) is None and b.value(key) is not None:
                    return True
                elif a.value(key) is not None and b.value(key) is None:
                    return False
                elif toDouble(a.value(key)) < toDouble(b.value(key)):
                    return True
                elif toDouble(a.value(key)) > toDouble(b.value(key)):
                    return False
        return False
