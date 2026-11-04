import sys

from ..result import XkorResult
from ..variant import toDouble, toInt, toString
from .abstractparadigm import XkorAbstractParadigm
from .comparators.basicresultcomparator import XkorBasicResultComparator


class XkorOrdinalParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["standard"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in ordinal paradigm", file=sys.stderr)

    def comparisonFunction(self, type=""):
        comparisonOpt = dict(self.opt)
        comparisonOpt["sortOrder"] = "descending"
        return XkorBasicResultComparator(type, comparisonOpt)

    def scorinate(self, athletes, previousResults=None):
        if not self._checkRequiredValues("XkorOrdinalParadigm::output(XkorResults *)"):
            return

        # initialize results
        self.out = []
        self.res = []

        statusSortOrder = self.readOptionList("statusSortOrder")
        statuses = self.readOptionList("statuses")

        for i in athletes:
            r = XkorResult()
            r.athlete = i.clone()
            status = self.generateStatus()
            if status == "":
                r.setScore(self.generateScore(i.rpSkill))
            else:
                # QList::indexOf(status) over the statuses list
                statusIndex = -1
                for idx in range(len(statuses)):
                    if toString(statuses[idx]) == status:
                        statusIndex = idx
                        break
                r.setScore(self.generateScore(i.rpSkill)
                           - toDouble(statusSortOrder[statusIndex]))
                r.setScoreString(status)
            self.res.append(r)

        self.comparisonFunction().sort(self.res)

        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 3)) + 2

        acc = 1
        for i in self.res:
            output = self.formatName(i.athlete.name, i.athlete.nation).ljust(nameWidth)
            if i.score() < 0:
                output += i.scoreString().rjust(resultWidth)
            else:
                output += str(acc).rjust(resultWidth)
            i.setOutput(output)
            self.out.append((i.athlete.name, output))
            acc += 1

    # protected:

    def generateScore(self, skill):
        attackModifier = toDouble(self.opt.get("attackModifier"))
        return ((self.s.randWeighted(skill) + attackModifier * self.s.randUniform())
                / (1 + attackModifier))
