import math
import sys

from ..result import XkorResult
from ..variant import toDouble, toInt
from .abstractparadigm import XkorAbstractParadigm
from .comparators.highjumpresultcomparator import XkorHighJumpResultComparator


class XkorHighJumpParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["standard"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in high jump paradigm", file=sys.stderr)

    def comparisonFunction(self, type=""):
        return XkorHighJumpResultComparator(type, self.opt)

    def scorinate(self, athletes, previousResults=None):
        if not self._checkRequiredValues("XkorHighJumpParadigm::output(XkorResults *)"):
            return

        # load options
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 3)) + 2

        heights = self.readOptionList("heights")
        attemptsPerHeight = toInt(self.opt.get("attemptsPerHeight"))
        displayDigits = toInt(self.opt.get("displayDigits"))

        # initialize results
        self.out = []
        self.res = []

        for athlete in athletes:
            r = XkorResult()
            r.athlete = athlete.clone()
            resultString = self.formatName(athlete.name, athlete.nation).ljust(nameWidth)
            bestHeight = 0.0
            for i in heights:
                failures = 0
                for j in range(attemptsPerHeight):
                    success = self.generateScore(athlete.rpSkill, toDouble(i))
                    if not success:
                        failures += 1
                    else:
                        break

                subResult = "x" * failures  # QString(failures, 'x')
                if failures < attemptsPerHeight:
                    bestHeight = toDouble(i)
                    subResult += "o"
                resultString += subResult.rjust(resultWidth)
                r.setScore(bestHeight)
                if failures == attemptsPerHeight:
                    break
                else:
                    r.result["lastHeightFailures"] = failures
                    r.result["failures"] = toInt(r.value("failures")) + failures

            # show final result
            resultString = (resultString.ljust(nameWidth + resultWidth * len(heights))
                            + f"{bestHeight:.{displayDigits}f}".rjust(resultWidth))

            if "decathlonA" in self.opt:
                a = toDouble(self.opt.get("decathlonA"))
                b = toDouble(self.opt.get("decathlonB"))
                c = toDouble(self.opt.get("decathlonC"))
                multiplier = toDouble(self.opt.get("decathlonMultiplier", 1))

                roundedValue = toDouble(
                    f"{bestHeight:.{toInt(self.opt.get('displayDigits'))}f}")

                if bestHeight == 0:
                    decathlonPoints = 0
                else:
                    decathlonPoints = int(math.floor(a * math.pow(multiplier * roundedValue - b, c)))

                resultString += str(decathlonPoints).rjust(resultWidth)

            r.setOutput(resultString)
            self.out.append((athlete.name, resultString))

            self.res.append(r)

    # protected:

    def adjustSkill(self, realSkill):
        rankModifier = toDouble(self.opt.get("rankModifier", 0))
        rankAdjustmentFactor = toDouble(self.opt.get("rankAdjustmentFactor", 1))

        # randomize the skill a bit to compensate for the fact that long
        # sequences of arrows would otherwise be highly predictable
        rval = (realSkill + self.s.randUniform() * rankModifier) / (1 + rankModifier)
        rval = rval * rankAdjustmentFactor + (1 - rankAdjustmentFactor) / 2
        return rval

    def individualResult(self, a, b, c=None):
        return XkorResult()  # unused

    def generateScore(self, skill, height):
        attackModifier = toDouble(self.opt.get("attackModifier"))
        rand = ((self.s.randWeighted(skill) + self.s.randUniform() * attackModifier)
                / (1 + attackModifier))

        threshold = (toDouble(self.opt.get("baseProb"))
                     * math.pow(toDouble(self.opt.get("depreciation")),
                                toDouble(self.opt.get("depreciationCoefficient")) * height
                                - toDouble(self.opt.get("depreciationBase"))))

        # (1 - rand) is used so that good athletes do well rather than poorly :)
        return (1 - rand) < threshold
