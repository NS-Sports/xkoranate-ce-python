from ..result import XkorResult
from ..variant import toDouble, toString
from .abstractparadigm import XkorAbstractParadigm
from .sqisparadigm import XkorSQISParadigm


class XkorH2HParadigm(XkorSQISParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.requiredValues = []
        self.requiredValues.append("score")

    def newAthleteWidget(self):
        # deliberately reaches past XkorAbstractH2HParadigm's style-aware
        # override (inherited via SQIS) to the plain widget — not super()
        return XkorAbstractParadigm.newAthleteWidget(self)

    def newOptionsWidget(self, paradigmOptions):
        from .options.timedparadigmoptions import XkorTimedParadigmOptions
        return XkorTimedParadigmOptions(paradigmOptions)

    # protected:

    def generateETScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        scoreType = ("score" if str_ == "" else str_)
        home.result[scoreType] = (toDouble(home.value(scoreType))
                                  + int(self.s.h2hScore("etScore", home.athlete.rpSkill,
                                                        away.athlete.rpSkill)))
        away.result[scoreType] = (toDouble(away.value(scoreType))
                                  + int(self.s.h2hScore("etScore", away.athlete.rpSkill,
                                                        home.athlete.rpSkill)))

        return (home, away)

    def generateFTScore(self, home, away):
        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        statuses = self.readOptionList("statuses")
        statusProbs = self.readOptionList("statusProbs")

        for i in range(len(statuses)):
            if self.s.randUniform() < toDouble(statusProbs[i]):  # HOMETEAMISTRY FAIL
                hRes.setScore(self._worstScore())
                hRes.result["status"] = toString(statuses[i])
                aRes.setScore(-self._worstScore())
                return (hRes, aRes)
            elif self.s.randUniform() < toDouble(statusProbs[i]):  # AWAYTEAMISTRY FAIL
                aRes.setScore(self._worstScore())
                aRes.result["status"] = toString(statuses[i])
                hRes.setScore(-self._worstScore())
                return (hRes, aRes)

        hRes.setScore(int(self.s.h2hScore("score", home.rpSkill, away.rpSkill)))
        aRes.setScore(int(self.s.h2hScore("score", away.rpSkill, home.rpSkill)))

        return (hRes, aRes)

    def generateGGScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        goldenGoalProb = toDouble(self.opt.get("goldenGoalProb"))

        scoreType = ("score" if str_ == "" else str_)

        if self.s.randUniform() < goldenGoalProb:  # someone scored; who was it?
            otScore1 = self.s.randWeightedH2H(home.athlete.rpSkill, away.athlete.rpSkill)
            otScore2 = self.s.randWeightedH2H(away.athlete.rpSkill, home.athlete.rpSkill)

            if otScore1 > otScore2:
                home.result[scoreType] = toDouble(home.value(scoreType)) + 1
            else:
                away.result[scoreType] = toDouble(away.value(scoreType)) + 1
        return (home, away)
