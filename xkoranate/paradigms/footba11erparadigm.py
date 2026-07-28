from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .abstractparadigm import XkorAbstractParadigm
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorFootba11erParadigm(XkorAbstractH2HParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)

    def hasOptionsWidget(self):
        return True

    def usesMaxSkill(self):
        # generateFTScore/GGScore below only ever compare
        # home.rpSkill / (home.rpSkill + away.rpSkill) between the two
        # specific competitors, which is invariant to any common rescale
        return False

    def newAthleteWidget(self):
        return XkorAbstractParadigm.newAthleteWidget(self)

    def newOptionsWidget(self, paradigmOptions):
        from .options.footba11erparadigmoptions import XkorFootba11erParadigmOptions
        return XkorFootba11erParadigmOptions(paradigmOptions, self._defaultHomeAdvantageMagnitude())

    # protected:

    def _defaultHomeAdvantageMagnitude(self):
        return toDouble(self.opt.get("homeAdvantage", 0.065))

    def homeAdvantageMagnitude(self):
        # the sport file provides a default magnitude; the options widget
        # lets the user override it per-event
        return toDouble(self.userOpt.get("homeAdvantageMagnitude", self._defaultHomeAdvantageMagnitude()))

    def generateFTScore(self, home, away):
        # get the parameters
        homeAdvantage = 0
        if toString(self.userOpt.get("homeAdvantage")) == "true":
            homeAdvantage = self.homeAdvantageMagnitude()
        skillCoeff = toDouble(self.opt.get("skillCoeff", 0.6))
        skillOffset = toDouble(self.opt.get("skillOffset", 0.2))
        listAttackStyle = (toString(self.opt.get("attackStyle", "list")) == "list")
        maxAttacks = toInt(self.opt.get("maxAttacks", 25))
        pointValues = toList(self.opt.get("pointValues", [1]))
        pointProbs = toList(self.opt.get("pointProbs", [1]))

        # if the home and away skill are both 0, we can’t calculate the ratio,
        # and use 0.5 instead
        skillRatio = (0.5 if home.rpSkill == away.rpSkill
                      else home.rpSkill / (home.rpSkill + away.rpSkill))
        homeSkill = skillCoeff * skillRatio + skillOffset + homeAdvantage

        if listAttackStyle:
            attackProbs = toList(self.opt.get(
                "attackProbs",
                [0.08, 0.2, 0.24, 0.2, 0.12, 0.08, 0.04, 0.0224, 0.0096,
                 0.0048, 0.0016, 0.00112, 0.00048]))
            rand = self.s.randUniform()
            acc = 0.0
            attacks = 0
            while attacks < len(attackProbs):
                acc += toDouble(attackProbs[attacks])
                if acc > rand:
                    break
                attacks += 1
        else:  # attackStyle == "normal"
            meanAttacks = toDouble(self.opt.get("meanAttacks", 8.11))
            stDevAttacks = toDouble(self.opt.get("stDevAttacks", 2.85))
            tailCutoff = toDouble(self.opt.get("attacksTailCutoff", 0.005))
            attacks = int(self.s.randGaussianCapped(tailCutoff) * stDevAttacks
                          + meanAttacks + 0.5)  # 0.5 for rounding

        homeAttacks = []
        awayAttacks = []
        i = 0
        while i < attacks and i < maxAttacks:
            # how many points will be scored
            attackValue = 0
            rand = self.s.randUniform()
            acc = 0.0
            for j in range(min(len(pointValues), len(pointProbs))):
                acc += toDouble(pointProbs[j])
                if acc > rand:
                    attackValue = toInt(pointValues[j])
                    break

            # who gets those points?
            if self.s.randUniform() < homeSkill:
                homeAttacks.append(attackValue)
                awayAttacks.append(0)
            else:
                homeAttacks.append(0)
                awayAttacks.append(attackValue)
            i += 1

        # add up the scores
        homeScore = 0
        awayScore = 0
        for i in range(attacks):
            homeScore += toInt(homeAttacks[i % maxAttacks])
            awayScore += toInt(awayAttacks[i % maxAttacks])

        # add up the subscores
        homeSubScores = []
        awaySubScores = []
        for i in range(len(pointValues)):
            homeSubScore = 0
            awaySubScore = 0
            for j in range(attacks):
                if toInt(homeAttacks[j % maxAttacks]) == toInt(pointValues[i]):
                    homeSubScore += 1
                elif toInt(awayAttacks[j % maxAttacks]) == toInt(pointValues[i]):
                    awaySubScore += 1
            homeSubScores.append(homeSubScore)
            awaySubScores.append(awaySubScore)

        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        hRes.setScore(homeScore)
        aRes.setScore(awayScore)
        hRes.result["subScores"] = homeSubScores
        aRes.result["subScores"] = awaySubScores

        return (hRes, aRes)

    def generateGGScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        scoreType = ("score" if str_ == "" else str_)
        subScoreType = ("subScores" if str_ == "" else str_ + "SubScores")

        # get the parameters
        homeAdvantage = 0
        if toString(self.userOpt.get("homeAdvantage")) == "true":
            homeAdvantage = self.homeAdvantageMagnitude()
        skillCoeff = toDouble(self.opt.get("skillCoeff", 0.6))
        skillOffset = toDouble(self.opt.get("skillOffset", 0.2))
        pointValues = toList(self.opt.get("pointValues", [1]))
        pointProbs = toList(self.opt.get("pointProbs", [1]))

        # if the home and away skill are both 0, we can’t calculate the ratio,
        # and use 0.5 instead
        skillRatio = (0.5 if home.athlete.rpSkill == away.athlete.rpSkill
                      else home.athlete.rpSkill / (home.athlete.rpSkill + away.athlete.rpSkill))
        homeSkill = skillCoeff * skillRatio + skillOffset + homeAdvantage

        # how many points will be scored?
        attackValue = 0
        rand = self.s.randUniform()
        acc = 0.0
        for i in range(min(len(pointValues), len(pointProbs))):
            acc += toDouble(pointProbs[i])
            if acc > rand:
                attackValue = toInt(pointValues[i])
                break

        # who gets those points?
        homeWin = False
        if self.s.randUniform() < homeSkill:
            homeWin = True

        # add the score
        if homeWin:
            home.result[scoreType] = toInt(home.result.get(scoreType)) + attackValue
        else:
            away.result[scoreType] = toInt(away.result.get(scoreType)) + attackValue

        # add the subscore
        homeSubScores = toList(home.value(subScoreType))
        awaySubScores = toList(away.value(subScoreType))
        for i in range(len(pointValues)):
            if toInt(pointValues[i]) == attackValue:
                if homeWin:
                    homeSubScores[i] = toInt(homeSubScores[i]) + 1
                else:
                    awaySubScores[i] = toInt(awaySubScores[i]) + 1
        home.result[subScoreType] = homeSubScores
        away.result[subScoreType] = awaySubScores

        return (home, away)

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        return -1  # we don’t use this
