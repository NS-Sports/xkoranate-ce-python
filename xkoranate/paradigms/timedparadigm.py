import math
import sys

from ..result import XkorResult
from ..variant import toBool, toDouble, toInt, toList, toString
from .abstractparadigm import XkorAbstractParadigm
from .comparators.timedresultcomparator import XkorTimedResultComparator


class XkorTimedParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["standard"] = True
        self.supportedCompetitions["multipleRun"] = True

    # protected:

    def comparisonFunction(self, type=""):
        return XkorTimedResultComparator(type, self.opt)

    @staticmethod
    def compareVariant(a, b):
        return toDouble(a) < toDouble(b)

    @staticmethod
    def compareVariantDescending(a, b):
        return toDouble(b) < toDouble(a)

    def formatScore(self, score):
        return self.timeFormat(score, toInt(self.opt.get("displayDigits")))

    def hasOptionsWidget(self):
        return True

    def newOptionsWidget(self, paradigmOptions):
        from .options.timedparadigmoptions import XkorTimedParadigmOptions
        return XkorTimedParadigmOptions(paradigmOptions)

    def calculateTotal(self, r):
        if toString(self.opt.get("totalType")) == "best":
            attempts = toList(r.result.get("attempts"))
            if toString(self.opt.get("sortOrder", "ascending")) == "ascending":
                attempts.sort(key=toDouble)
            else:
                attempts.sort(key=toDouble, reverse=True)
            r.setScore(toDouble(attempts[0]))
            for j in range(len(attempts)):
                if toList(r.result.get("attempts"))[j] == r.result.get("score"):
                    r.setScoreString(toString(toList(r.result.get("attemptStrings"))[j]))
        else:
            sum_ = 0.0
            attempts = toList(r.result.get("attempts"))

            # check if any of the scores are failures
            for i in range(len(attempts)):
                if (toDouble(toList(r.result.get("attempts"))[i]) == sys.float_info.max
                        or toDouble(toList(r.result.get("attempts"))[i]) == sys.float_info.min):
                    r.setScore(toDouble(toList(r.result.get("attempts"))[i]))
                    r.setScoreString(toString(toList(r.result.get("attemptStrings"))[i]))
                    r.setOutput(self.outputLine(r))
                    return

            for j in attempts:
                sum_ += toDouble(j)
            r.setScore(sum_)
            r.setScoreString(self.formatScore(sum_))

        r.setOutput(self.outputLine(r))

    def individualResult(self, ath, type="", roundingType=""):
        statuses = self.readOptionList("statuses")
        statusProbs = self.readOptionList("statusProbs")
        advancementProbs = self.readOptionList("advancementProbs")

        for i in range(len(statuses)):
            if self.s.randUniform() < toDouble(statusProbs[i]):
                rval = XkorResult(
                    (sys.float_info.max
                     if toString(self.opt.get("sortOrder", "ascending")) == "ascending"
                     else -sys.float_info.max),
                    toString(statuses[i]), ath)
                if (i < len(advancementProbs)
                        and self.s.randUniform() < toDouble(advancementProbs[i])):
                    rval.result["causesAdvancement"] = True
                return rval

        # if there was no status…
        score = self.s.individualScore(type, ath.rpSkill)
        if "lapped" in self.opt and score == toDouble(self.opt.get("lappedValue")):
            return XkorResult(
                (sys.float_info.max
                 if toString(self.opt.get("sortOrder", "ascending")) == "ascending"
                 else -sys.float_info.max),
                toString(self.opt.get("lapped")), ath)
        else:
            return XkorResult(self.roundScore(score, roundingType),
                              self.formatScore(self.roundScore(score, roundingType)),
                              ath)

    def outputLine(self, r):
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 5)) + 2

        rval = self.formatName(r.athlete.name, r.athlete.nation).ljust(nameWidth)
        attemptStrings = toList(r.value("attemptStrings"))
        for i in attemptStrings:
            rval += toString(i).rjust(resultWidth)

        if toInt(self.opt.get("attempts")) > 1 or toInt(self.userOpt.get("runNumber")) > 0:
            # only show the overall score if there’s more than one attempt
            rval += r.scoreString().rjust(
                2 + resultWidth * ((1 + toInt(self.userOpt.get("runNumber")))
                                   * (toInt(self.opt.get("attempts", 1))
                                      + toInt(self.opt.get("furtherAttempts")))
                                   - len(toList(r.value("attempts"))) + 1))

        if "decathlonA" in self.opt:
            a = toDouble(self.opt.get("decathlonA"))
            b = toDouble(self.opt.get("decathlonB"))
            c = toDouble(self.opt.get("decathlonC"))
            multiplier = toDouble(self.opt.get("decathlonMultiplier", 1))

            roundedValue = (int(r.score() * math.pow(10.0, toDouble(self.opt.get("displayDigits"))) + 1)
                            * math.pow(10.0, -toDouble(self.opt.get("displayDigits"))))

            if toString(self.opt.get("sortOrder", "ascending")) == "ascending":
                if r.score() == sys.float_info.max:
                    decathlonPoints = 0
                else:
                    decathlonPoints = int(math.floor(a * math.pow(b - multiplier * roundedValue, c)))
            else:
                if r.score() == -sys.float_info.max:
                    decathlonPoints = 0
                else:
                    decathlonPoints = int(math.floor(a * math.pow(multiplier * roundedValue - b, c)))

            rval += str(decathlonPoints).rjust(resultWidth)

        return rval

    def roundScore(self, score, roundingType=""):
        tiebreakerDigits = "tiebreakerDigits"
        roundingValue = "roundingValue"
        displayDigits = "displayDigits"
        if roundingType != "":
            tiebreakerDigits = roundingType + "TiebreakerDigits"
            roundingValue = roundingType + "RoundingValue"
            displayDigits = roundingType + "DisplayDigits"

        if tiebreakerDigits in self.opt:
            rounding = math.pow(10.0, -toDouble(self.opt.get(tiebreakerDigits)))
        elif roundingValue in self.opt:
            rounding = toDouble(self.opt.get(roundingValue))
        else:
            rounding = math.pow(10.0, -toDouble(self.opt.get(displayDigits)))

        if score == sys.float_info.max or score == -sys.float_info.max:
            return score
        elif int(score / rounding) == score / rounding:
            return int(score / rounding) * rounding
        else:
            return int(score / rounding + 1) * rounding

    def scorinate(self, athletes, previousResults=None):
        if previousResults is None:
            previousResults = []

        # check that we can use the sport
        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i,
                      "in XkorAbstractParadigm::scorinate(QList<XkorAthlete>)",
                      file=sys.stderr)
                self.out.append(("", "Sport does not support this paradigm"))
                return

        # initialize results
        self.out = []
        self.res = []

        attemptTypes = self.readOptionList("attemptTypes")

        for i in athletes:
            r = XkorResult()
            r.athlete = i.clone()

            # load up the previous result, if any
            for j in previousResults:
                if j.athlete == i:
                    attempts = toList(r.result.get("attempts"))
                    attemptStrings = toList(r.result.get("attemptStrings"))
                    attempts.extend(toList(j.result.get("attempts")))
                    attemptStrings.extend(toList(j.result.get("attemptStrings")))
                    r.result["attempts"] = attempts
                    r.result["attemptStrings"] = attemptStrings

            priorAttempts = len(toList(r.result.get("attempts")))
            for j in range(priorAttempts, priorAttempts + toInt(self.opt.get("attempts", 1))):
                attemptTypeCount = len(attemptTypes)
                print(j, attemptTypeCount, file=sys.stderr)
                if attemptTypeCount > 0 and j >= attemptTypeCount:
                    result = self.individualResult(i, toString(attemptTypes[attemptTypeCount - 1]))
                elif attemptTypeCount > 0:
                    result = self.individualResult(i, toString(attemptTypes[j]))
                else:
                    result = self.individualResult(i, "score")
                attempts = toList(r.result.get("attempts"))
                attemptStrings = toList(r.result.get("attemptStrings"))
                attempts.append(result.score())
                attemptStrings.append(result.scoreString())
                r.result["attempts"] = attempts
                r.result["attemptStrings"] = attemptStrings
                if "causesAdvancement" in result.result:
                    r.result["causesAdvancement"] = result.value("causesAdvancement")
                if (toString(self.opt.get("totalType")) != "best"
                        and (result.score() == sys.float_info.max
                             or result.score() == -sys.float_info.max)):
                    break
            self.calculateTotal(r)

            self.res.append(r)

        # figure out who was advanced
        if (toString(self.userOpt.get("allowAdvancement", "true")) == "true"
                and "spontaneousAdvancementProb" in self.opt):
            for i in self.res:
                if (i.score() != sys.float_info.max and i.score() != -sys.float_info.max
                        and self.s.randUniform() < toDouble(self.opt.get("spontaneousAdvancementProb"))):
                    i.result["advanced"] = True
                    i.setOutput(i.output() + "  ADV")
        if (toString(self.userOpt.get("allowAdvancement", "true")) == "true"
                and "advancementProbs" in self.opt):
            advancements = 0
            for i in self.res:
                if "causesAdvancement" in i.result:
                    advancements += 1
            print(advancements, file=sys.stderr)

            self.comparisonFunction().sort(self.res)
            for i in range(advancements):
                rand = int(self.s.individualScore("advancer"))

                # find the lowest-ranked athlete that fits the criteria
                advancedIndex = len(self.res) - 1
                while advancedIndex > 0:
                    if (self.res[advancedIndex].score() == sys.float_info.max
                            or self.res[advancedIndex].score() == -sys.float_info.max
                            or toBool(self.res[advancedIndex].result.get("advanced")) == True):
                        advancedIndex -= 1
                    elif rand > 0:
                        advancedIndex -= 1
                        rand -= 1
                    else:
                        self.res[advancedIndex].result["advanced"] = True
                        self.res[advancedIndex].setOutput(
                            self.res[advancedIndex].output() + "  ADV")
                        break

        if "furtherAttempts" in self.opt:
            self.comparisonFunction().sort(self.res)
            for i in range(toInt(self.opt.get("furtherAttemptCutoff"))):
                r = self.res[i].clone()
                for j in range(toInt(self.opt.get("furtherAttempts"))):
                    result = self.individualResult(r.athlete, "score")
                    attempts = toList(r.result.get("attempts"))
                    attemptStrings = toList(r.result.get("attemptStrings"))
                    attempts.append(result.score())
                    attemptStrings.append(result.scoreString())
                    r.result["attempts"] = attempts
                    r.result["attemptStrings"] = attemptStrings

                self.calculateTotal(r)
                self.res[i] = r

        self.generateOutput()
