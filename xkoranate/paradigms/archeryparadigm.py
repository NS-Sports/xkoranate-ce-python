from ..result import XkorResult
from ..variant import toDouble, toInt, toString
from .abstractparadigm import XkorAbstractParadigm
from .comparators.archeryresultcomparator import XkorArcheryResultComparator


class XkorArcheryParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["archery"] = True
        self.supportedCompetitions["matches"] = True

    def breakTie(self, athletes, type=""):
        maxScore = toInt(self.opt.get("maxScore", 0))
        scorePointForX = (toString(self.opt.get("scorePointForX")) == "true")
        if type == "lots" or type == "closest":
            for i in athletes:
                result = self.findResult(i.id)
                result.result["lots"] = self.s.randUniform()
                if type == "closest":
                    result.setOutput(result.output() + " (closest arrow)")
                else:
                    result.setOutput(result.output() + " (drawing of lots)")
        elif toString(self.userOpt.get("rankingRound")) == "true":
            for i in athletes:
                result = self.findResult(i.id)
                score = 0
                for j in range(toInt(self.opt.get("arrowsPerTiebreak"))):
                    if maxScore != 0 and not scorePointForX:
                        score += min(self.generateArrowScore(self.adjustSkill(i.skill)), maxScore)
                    else:
                        score += self.generateArrowScore(self.adjustSkill(i.skill))
                result.result["tbScore"] = (
                    toDouble(result.result.get("tbScore"))
                    + score / pow(toDouble(self.opt.get("maxScore")) * 2,
                                  toDouble(result.result.get("tbArrows"))))
                result.result["tbArrows"] = toDouble(result.result.get("tbArrows")) + 1
                if result.output()[-1:] == ")":
                    result.setOutput(result.output()[:len(result.output()) - 1]
                                     + " " + str(score) + ")")
                else:
                    result.setOutput(result.output() + " (tiebreak: " + str(score) + ")")
        else:
            for home, away in self._pairs(athletes):
                homeScore = 0
                awayScore = 0
                tries = 0
                homeLots = 0.0
                awayLots = 0.0
                while homeScore == awayScore and tries < 3:
                    for i in range(toInt(self.opt.get("arrowsPerTiebreak"))):
                        if maxScore != 0 and not scorePointForX:
                            homeScore += min(self.generateArrowScore(self.adjustSkill(home.skill)), maxScore)
                            awayScore += min(self.generateArrowScore(self.adjustSkill(away.skill)), maxScore)
                        else:
                            homeScore += self.generateArrowScore(self.adjustSkill(home.skill))
                            awayScore += self.generateArrowScore(self.adjustSkill(away.skill))
                    tries += 1
                if homeScore == awayScore:
                    homeLots = self.s.randUniform()
                    awayLots = self.s.randUniform()
                    self.findResult(home.id).result["lots"] = homeLots
                    self.findResult(away.id).result["lots"] = awayLots

                result = self.findResult(away.id)
                if homeLots > awayLots:
                    result.setOutput(result.output() + " (tiebreak: " + str(homeScore)
                                     + "*–" + str(awayScore) + ")")
                elif awayLots > homeLots:
                    result.setOutput(result.output() + " (tiebreak: " + str(homeScore)
                                     + "–" + str(awayScore) + "*)")
                else:
                    result.setOutput(result.output() + " (tiebreak: " + str(homeScore)
                                     + "–" + str(awayScore) + ")")

                # let the competition know who won
                self.findResult(home.id).result["tbScore"] = homeScore
                self.findResult(away.id).result["tbScore"] = awayScore
        self.generateOutput()

    def comparisonFunction(self, type=""):
        if toString(self.userOpt.get("rankingRound")) == "true":
            return XkorArcheryResultComparator("rankingRound", self.opt)
        else:
            return XkorArcheryResultComparator(type, self.opt)

    def scorinate(self, athletes, previousResults=None):
        if not self._checkRequiredValues("XkorArcheryParadigm::output(XkorResults *)"):
            return

        # load options
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 3)) + 2

        isRankingRound = (toString(self.userOpt.get("rankingRound")) == "true")

        if isRankingRound:
            arrows = toInt(self.opt.get("rankingArrows"))
        else:
            arrows = toInt(self.opt.get("knockoutArrows"))

        maxScore = toInt(self.opt.get("maxScore"))

        # initialize results
        self.out = []
        self.res = []

        i = 0
        homeScore = ""
        for athlete in athletes:
            score = 0
            tens = 0
            Xs = 0
            for j in range(arrows):
                arrowScore = self.generateArrowScore(
                    self.adjustSkill(athlete.rpSkill, isRankingRound))
                if "maxScore" in self.opt:
                    if toString(self.opt.get("scorePointForX")) == "true":
                        # if an X counts at face value
                        score += arrowScore
                    else:  # if an X counts the same as a 10
                        score += min(maxScore, arrowScore)

                    if arrowScore >= maxScore:
                        tens += 1
                    if arrowScore > maxScore:
                        Xs += 1
                else:
                    score += arrowScore

            result = ""
            if toString(self.userOpt.get("rankingRound")) == "true":
                result = self.formatName(athlete).ljust(nameWidth)
                result += str(score).rjust(resultWidth)
                if "maxScore" in self.opt:
                    result += str(tens).rjust(resultWidth)
                    result += str(Xs).rjust(resultWidth)
            else:
                if i & 1:
                    result = homeScore + "–" + str(score) + " " + self.formatName(athlete)
                else:
                    homeScore = self.formatName(athlete) + " " + str(score)
            r = XkorResult(score, ath=athlete.clone())
            r.setOutput(result)
            r.result["tens"] = tens
            r.result["Xs"] = Xs
            self.res.append(r)
            i += 1
        self.generateOutput()

    # protected:

    def adjustSkill(self, realSkill, isRankingRound=False):
        return self._adjustSkill(realSkill, "ranking" if isRankingRound else "knockout")

    def generateArrowScore(self, skill):
        return int(self.s.individualScore("score", skill))
