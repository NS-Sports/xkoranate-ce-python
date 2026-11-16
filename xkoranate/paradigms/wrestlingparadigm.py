import sys

from ..result import XkorResult
from ..variant import toDouble, toString
from .abstractparadigm import XkorAbstractParadigm


class XkorWrestlingParadigmResult:
    def __init__(self, homeScore=0.0, awayScore=0.0, result="", reversedResult="",
                 annotation=""):
        self.homeScore = homeScore
        self.awayScore = awayScore
        self.result = result
        self.reversedResult = reversedResult
        self.annotation = annotation

    def reverse(self):
        return XkorWrestlingParadigmResult(self.awayScore, self.homeScore,
                                           self.reversedResult, self.result,
                                           self.annotation)


class XkorWrestlingParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["matches"] = True
        self.supportedCompetitions["roundRobin"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in wrestling paradigm", file=sys.stderr)

    def scorinate(self, athletes, previousResults=None):
        if not self._checkRequiredValues("XkorWrestlingParadigm::output(XkorResults *)"):
            return

        # initialize results
        self.out = []
        self.res = []

        for home, away in self._pairs(athletes):
            score = self.generateScore(home.rpSkill, away.rpSkill)
            result = (self.formatName(home) + " " + score.result + " "
                      + self.formatName(away))
            if score.annotation != "":
                result += " (" + score.annotation + ")"

            self.out.append((home.name, result))
            self.res.append(XkorResult(score.homeScore, ath=home.clone()))
            self.res.append(XkorResult(score.awayScore, ath=away.clone()))

    # protected:

    def generateScore(self, homeSkill, awaySkill):
        rval = XkorWrestlingParadigmResult()

        probArr = []  # QList<QPair<XkorWrestlingParadigmResult, double> >

        results = self.readOptionList("results")
        reversedResults = self.readOptionList("reversedResults")
        winnerScores = self.readOptionList("winnerScores")
        loserScores = self.readOptionList("loserScores")
        resultProbs = self.readOptionList("resultProbs")
        annotations = self.readOptionList("annotations")

        if len(results) == 0 and len(reversedResults) == 0:  # generate these automatically
            for i in range(min(len(winnerScores), len(loserScores))):
                results.append(toString(winnerScores[i]) + "–" + toString(loserScores[i]))
                reversedResults.append(toString(loserScores[i]) + "–" + toString(winnerScores[i]))

        for i in range(min(len(results), len(reversedResults), len(winnerScores),
                           len(loserScores), len(resultProbs))):
            if i < len(annotations):
                r = XkorWrestlingParadigmResult(toDouble(winnerScores[i]),
                                                toDouble(loserScores[i]),
                                                toString(results[i]),
                                                toString(reversedResults[i]),
                                                toString(annotations[i]))
            else:
                r = XkorWrestlingParadigmResult(toDouble(winnerScores[i]),
                                                toDouble(loserScores[i]),
                                                toString(results[i]),
                                                toString(reversedResults[i]))
            probArr.append((r, toDouble(resultProbs[i])))

        homeRand = self.s.randWeightedH2H(homeSkill, awaySkill)
        awayRand = self.s.randWeightedH2H(awaySkill, homeSkill)

        if homeRand - awayRand > -toDouble(self.opt.get("mandatoryHomeAdvantage", 0)):
            difference = self.s.randWeightedH2H(homeSkill, awaySkill)
        else:
            difference = self.s.randWeightedH2H(awaySkill, homeSkill)

        acc = 0.0
        chosen = probArr[-1][0] if probArr else None
        for i in probArr:
            acc += i[1]
            if difference < acc:
                chosen = i[0]
                break
        # a draw past every outcome (probabilities that add up to less than
        # 1, or fall short by rounding) takes the last one rather than
        # leaving a blank 0–0 the sport can't produce
        if chosen is not None:
            rval = chosen if homeRand > awayRand else chosen.reverse()
        return rval
