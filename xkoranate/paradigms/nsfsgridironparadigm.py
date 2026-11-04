from ..result import XkorResult
from ..variant import toDouble, toInt, toString
from .abstractparadigm import XkorAbstractParadigm
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorNSFSGridironParadigm(XkorAbstractH2HParadigm):
    def newAthleteWidget(self):
        # deliberately reaches past XkorAbstractH2HParadigm's style-aware
        # override to the plain name/nation/skill widget — not super()
        return XkorAbstractParadigm.newAthleteWidget(self)

    def newOptionsWidget(self, paradigmOptions):
        from .options.nsfsgridironparadigmoptions import XkorNSFSGridironParadigmOptions
        return XkorNSFSGridironParadigmOptions(paradigmOptions)

    # protected:

    def generateConversions(self, count, forceValue=-1):
        rval = 0

        if forceValue == 1:  # third overtime
            conversionValue = toInt(self.opt.get("otConversionValue"))
            conversionProb = toDouble(self.opt.get("otConversionProb"))
        else:
            conversionValue = toInt(self.opt.get("conversionValue"))
            conversionProb = toDouble(self.opt.get("conversionProb"))

        i = 0
        while i < count:
            rand = self.s.randUniform()
            if rand < conversionProb:
                rval += conversionValue
            i += 1

        return rval

    def generateFTScore(self, home, away):
        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        periods = toInt(self.opt.get("periods"))
        if toString(self.userOpt.get("usePeriods", "true")) == "true":
            for i in range(periods):
                result = self.generateScorePair(home.rpSkill, away.rpSkill)
                hRes.setScore(hRes.score() + result[0])
                aRes.setScore(aRes.score() + result[1])
                self._appendSubScores(hRes, aRes, result[0], result[1])
        else:
            result = self.generateScorePair(home.rpSkill, away.rpSkill, periods)
            hRes.setScore(result[0])
            aRes.setScore(result[1])

        return (hRes, aRes)

    # C++ overloads generateScore: the QPair<int, int> version
    # generateScore(double skill, double oppSkill, int attackMultiplier = 1)
    # is renamed generateScorePair here; the six-argument int version keeps
    # the name generateScore (it overrides the base pure virtual).
    def generateScorePair(self, skill, oppSkill, attackMultiplier=1):
        # load constants
        pointValues = self.readOptionList("pointValues")
        scoringProbs = self.readOptionList("scoringProbs")
        scoringCoeffs = self.readOptionList("scoringCoeffs")
        turnoverBase = toDouble(self.opt.get("turnoverBase"))
        turnoverCoeff = toDouble(self.opt.get("turnoverCoeff"))
        attacksBase = toDouble(self.opt.get("attacksBase"))
        attacksCoeff = toDouble(self.opt.get("attacksCoeff"))

        rankDiff = skill - oppSkill

        homeAttacks = int(attacksBase + attacksCoeff * rankDiff)
        awayAttacks = int(attacksBase + attacksCoeff * -rankDiff)
        homeAttacks *= attackMultiplier
        awayAttacks *= attackMultiplier

        # calculate P(score), P(turnover) on any given attack
        homePScore = []
        awayPScore = []
        homePAcc = 0.0
        awayPAcc = 0.0
        for i in range(len(pointValues)):
            homeP = toDouble(scoringProbs[i]) + toDouble(scoringCoeffs[i]) * rankDiff
            awayP = toDouble(scoringProbs[i]) + toDouble(scoringCoeffs[i]) * -rankDiff
            homePScore.append(homeP / (1 - homePAcc))  # probability of this score once we know
            awayPScore.append(awayP / (1 - awayPAcc))  # we haven’t gotten the previous scores
            homePAcc += homeP
            awayPAcc += awayP
        homePTurnover = (turnoverBase + turnoverCoeff * rankDiff) / (1 - homePAcc)
        awayPTurnover = (turnoverBase + turnoverCoeff * -rankDiff) / (1 - awayPAcc)

        homeScore = 0
        awayScore = 0
        while homeAttacks > 0 or awayAttacks > 0:
            # home scores
            for i in range(len(pointValues)):
                j = self._binomialDraw(homeAttacks, homePScore[i], trace=True)
                if j >= 0:
                    homeScore += j * toInt(pointValues[i])
                    homeAttacks -= j  # use the remaining attacks for other purposes
                    if i == 0:
                        homeScore += self.generateConversions(j)
            # away scores
            for i in range(len(pointValues)):
                j = self._binomialDraw(awayAttacks, awayPScore[i], trace=True)
                if j >= 0:
                    awayScore += j * toInt(pointValues[i])
                    awayAttacks -= j  # use the remaining attacks for other purposes
                    if i == 0:
                        awayScore += self.generateConversions(j)

            # home turnovers
            turnovers = self._binomialDraw(homeAttacks, homePTurnover)
            if turnovers >= 0:
                awayAttacks = turnovers  # give the other team turnovers
            # away turnovers
            turnovers = self._binomialDraw(awayAttacks, awayPTurnover)
            if turnovers >= 0:
                homeAttacks = turnovers  # give the other turnovers
        return (homeScore, awayScore)

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        return -1  # we don’t use this
