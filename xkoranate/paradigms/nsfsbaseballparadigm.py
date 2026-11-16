import math

from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .nsfsgridironparadigm import XkorNSFSGridironParadigm


class XkorNSFSBaseballParadigm(XkorNSFSGridironParadigm):
    # protected:

    # a grand slam with the scores level is the widest a walk-off can be
    _walkOffMarginDefault = 4

    def generateETScore(self, hRes, aRes, str_=""):
        # one extra inning; the side listed first bats first, as in regulation
        hRes = hRes.clone()
        aRes = aRes.clone()
        result = self.generateScorePair(hRes.athlete.rpSkill, aRes.athlete.rpSkill)
        # the scores were level, so the side batting last trails by whatever
        # the other side just scored
        homeRuns = self._walkOffRuns(result[1], result[0], self._walkOffMarginDefault)
        hRes.setScore(hRes.score() + result[0])
        aRes.setScore(aRes.score() + homeRuns)
        self._appendSubScores(hRes, aRes, result[0], homeRuns)

        return (hRes, aRes)

    def generateFTScore(self, away, home):
        # note that we’ve reversed the parameters, because the home team bats second
        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        periods = toInt(self.opt.get("periods"))
        if toString(self.userOpt.get("usePeriods", "true")) == "true":
            for i in range(periods):
                result = self.generateScorePair(home.rpSkill, away.rpSkill)

                # is this the ninth inning?
                homeMustBat = True
                if i == periods - 1 and aRes.score() + result[1] < hRes.score():
                    homeMustBat = False

                aRes.setScore(aRes.score() + result[1])
                homeRuns = result[0]
                if i == periods - 1:
                    # the game ends the moment the home side goes ahead
                    homeRuns = self._walkOffRuns(homeRuns, aRes.score() - hRes.score(),
                                                 self._walkOffMarginDefault)
                if homeMustBat:
                    hRes.setScore(hRes.score() + homeRuns)
                hResScores = toList(hRes.result.get("subScores"))
                aResScores = toList(aRes.result.get("subScores"))
                if homeMustBat:
                    hResScores.append(homeRuns)
                aResScores.append(result[1])
                hRes.result["subScores"] = hResScores
                aRes.result["subScores"] = aResScores
        else:
            # because of the special ninth inning rule, we need to generate it separately
            result1 = self.generateScorePair(home.rpSkill, away.rpSkill, periods - 1)
            result2 = self.generateScorePair(home.rpSkill, away.rpSkill)

            if result1[1] + result2[1] < result1[0]:
                hRes.setScore(result1[0])  # home did not bat in ninth inning
            else:
                # the game ends the moment the home side goes ahead
                hRes.setScore(result1[0] + self._walkOffRuns(
                    result2[0], result1[1] + result2[1] - result1[0],
                    self._walkOffMarginDefault))
            aRes.setScore(result1[1] + result2[1])

        return (aRes, hRes)

    def generateScorePair(self, skill, oppSkill, attackMultiplier=1):
        # load constants
        baseScoringProb = toDouble(self.opt.get("baseScoringProb"))
        baseScoringCoeff = toDouble(self.opt.get("baseScoringCoeff"))
        extraScoringProb = toDouble(self.opt.get("extraScoringProb"))
        extraScoringCoeff = toDouble(self.opt.get("extraScoringCoeff"))

        # skills run from 0 to 1, so no two differ by more than 1. A wider
        # gap means skills that were never scaled, and it pushes the
        # probabilities below out of [0, 1): the runs loop then never ends,
        # and math.pow overflows.
        rankDiff = max(-1.0, min(1.0, oppSkill - skill))

        # calculate base probability and multiplier
        homeP = baseScoringProb + baseScoringCoeff * rankDiff
        awayP = baseScoringProb + baseScoringCoeff * -rankDiff

        homePMultiplier = extraScoringProb + extraScoringCoeff * rankDiff
        awayPMultiplier = extraScoringProb + extraScoringCoeff * -rankDiff

        homeScore = 0
        awayScore = 0

        for i in range(attackMultiplier):
            # home score
            rand = self.s.randUniform()
            acc = 0.0
            pJRuns = 1 - homeP  # probability of 0 runs
            j = 0
            while True:
                acc += pJRuns
                if rand < acc:
                    homeScore += j
                    break
                # calculate probability of i + 1 runs
                pJRuns = homeP * math.pow(homePMultiplier, j) * (1 - homePMultiplier)
                j += 1

            # away score
            rand = self.s.randUniform()
            acc = 0.0
            pJRuns = 1 - awayP  # probability of 0 runs
            j = 0
            while True:
                acc += pJRuns
                if rand < acc:
                    awayScore += j
                    break
                # calculate probability of i + 1 runs
                pJRuns = awayP * math.pow(awayPMultiplier, j) * (1 - awayPMultiplier)
                j += 1
        return (awayScore, homeScore)
