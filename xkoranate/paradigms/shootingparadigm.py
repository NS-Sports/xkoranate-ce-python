import sys

from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .comparators.shootingresultcomparator import XkorShootingResultComparator
from .scoredparadigm import XkorScoredParadigm


class XkorShootingParadigm(XkorScoredParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions = {}
        self.supportedCompetitions["shooting"] = True

    def breakTie(self, athletes, type=""):
        for i in athletes:
            result = self.findResult(i.id)

            ath = i.clone()
            ath.rpSkill = self.adjustSkill(ath.rpSkill, "shootoff")
            soResult = self.individualResult(ath, "shootoffScore", "shootoff")

            shootoffScores = toList(result.value("shootoffScores"))
            shootoffScores.append(soResult.score())
            result.result["shootoffScores"] = shootoffScores
            result.result["shootoffShots"] = toDouble(result.result.get("shootoffShots")) + 1
            if result.output()[-1:] == ")":
                result.setOutput(result.output()[:len(result.output()) - 1]
                                 + " " + self.formatShootoffScore(soResult.score()) + ")")
            else:
                result.setOutput(result.output() + " (shoot-off: "
                                 + self.formatShootoffScore(soResult.score()) + ")")

        self.generateOutput()

    def comparisonFunction(self, type=""):
        if toString(self.userOpt.get("qualifying")) == "true":
            return XkorShootingResultComparator("qualifying", self.opt)
        else:
            return XkorShootingResultComparator(type, self.opt)

    def scorinate(self, athletes, previousResults=None):
        if previousResults is None:
            previousResults = []

        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i,
                      "in XkorShootingParadigm::output(XkorResults *)",
                      file=sys.stderr)
                self.out.append(("", "Sport does not support this paradigm"))
                return

        # load options
        isQualifying = (toString(self.userOpt.get("qualifying")) == "true")

        if isQualifying:
            attempts = toInt(self.opt.get("qualifyingAttempts"))
            attemptType = "qualifyingScore"
            attemptTypes = "qualifyingAttemptTypes"
            roundingType = "qualifying"
        else:
            attempts = toInt(self.opt.get("finalAttempts"))
            attemptType = "finalScore"
            attemptTypes = "finalAttemptTypes"
            roundingType = "final"

        # initialize results
        self.out = []
        self.res = []

        for i in athletes:
            r = XkorResult()
            r.athlete = i.clone()

            # load up the previous result, if any
            for j in previousResults:
                if j.athlete == i:
                    attemptsList = toList(r.result.get("attempts"))
                    attemptStrings = toList(r.result.get("attemptStrings"))
                    attemptsList.append(j.score())
                    attemptStrings.append(j.scoreString())
                    r.result["attempts"] = attemptsList
                    r.result["attemptStrings"] = attemptStrings

            for j in range(attempts):
                # generate the result with a modified skill
                ath = i.clone()
                ath.rpSkill = self.adjustSkill(ath.rpSkill, attemptType)
                if attemptTypes in self.opt:
                    result = self.individualResult(ath, toString(self.readOptionList(attemptTypes)[j]))
                else:
                    result = self.individualResult(ath, attemptType, roundingType)

                attemptsList = toList(r.result.get("attempts"))
                attemptStrings = toList(r.result.get("attemptStrings"))
                attemptsList.append(result.score())
                attemptStrings.append(result.scoreString())
                r.result["attempts"] = attemptsList
                r.result["attemptStrings"] = attemptStrings
            self.calculateTotal(r)

            self.res.append(r)

        self.generateOutput()

    # protected:

    def adjustSkill(self, realSkill, roundType):
        rankModifier = toDouble(self.opt.get(roundType + "RankModifier", 0))
        rankAdjustmentFactor = toDouble(self.opt.get(roundType + "RankAdjustmentFactor", 1))

        # randomize the skill a bit to compensate for the fact that long
        # sequences of arrows would otherwise be highly predictable
        rval = (realSkill + self.s.randUniform() * rankModifier) / (1 + rankModifier)
        rval = rval * rankAdjustmentFactor + (1 - rankAdjustmentFactor) / 2
        return rval

    def formatScore(self, score):
        isQualifying = (toString(self.userOpt.get("qualifying")) == "true")
        displayDigits = (toInt(self.opt.get("qualifyingDisplayDigits")) if isQualifying
                         else toInt(self.opt.get("finalDisplayDigits")))
        return f"{score:.{displayDigits}f}"

    def formatShootoffScore(self, score):
        displayDigits = toInt(self.opt.get("shootoffDisplayDigits"))
        return f"{score:.{displayDigits}f}"

    def outputLine(self, r):
        isQualifying = (toString(self.userOpt.get("qualifying")) == "true")

        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        if isQualifying:
            resultWidth = toInt(self.opt.get("resultWidth", 3)) + 2
        else:
            resultWidth = toInt(self.opt.get("resultWidth", 5)) + 2

        rval = self.formatName(r.athlete.name, r.athlete.nation).ljust(nameWidth)
        attemptStrings = toList(r.value("attemptStrings"))
        for i in attemptStrings:
            rval += toString(i).rjust(resultWidth)

        if isQualifying:
            if toInt(self.opt.get("qualifyingAttempts")) > 1:
                rval += r.scoreString().rjust(
                    2 + resultWidth * (toInt(self.opt.get("qualifyingAttempts"))
                                       - len(toList(r.value("attempts"))) + 1))
        else:
            rval += r.scoreString().rjust(
                2 + resultWidth * (toInt(self.opt.get("finalAttempts"))
                                   - len(toList(r.value("attempts"))) + 2))

        return rval
