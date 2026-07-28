from ..result import XkorResult
from ..variant import qNumber, toDouble, toInt, toList, toString
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorHowzzatParadigm(XkorAbstractH2HParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)

    def hasOptionsWidget(self):
        return True

    def usesMaxSkill(self):
        # generateFTScore below only ever compares
        # home.rpSkill / (home.rpSkill + away.rpSkill) between the two
        # specific competitors, which is invariant to any common rescale
        return False

    def newOptionsWidget(self, paradigmOptions):
        from .options.howzzatparadigmoptions import XkorHowzzatParadigmOptions
        return XkorHowzzatParadigmOptions(paradigmOptions, self._defaultHomeAdvantageMagnitude())

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
        useStyleMods = toString(self.userOpt.get("useStyleMods", "true")) == "true"
        skillCoeff = toDouble(self.opt.get("skillCoeff", 0.6))
        skillOffset = toDouble(self.opt.get("skillOffset", 0.2))
        styleCoeff = toDouble(self.opt.get("styleCoeff", 0.04))
        maxOvers = toInt(self.opt.get("maxOvers", 50))
        maxBalls = toInt(self.opt.get("ballsPerOver", 6)) * maxOvers
        maxWickets = toInt(self.opt.get("maxWickets", 10))
        meanRunRate = toList(self.opt.get("meanRunRate", [3.52, 4.33, 4.88, 5.47, 6.55]))
        stDevRunRate = toList(self.opt.get("stDevRunRate", [0.39, 0.17, 0.21, 0.17, 0.69]))
        meanWicketRate = toList(self.opt.get("meanWicketRate", [23.63, 29.31, 35.45, 47.37, 96.6]))
        stDevWicketRate = toList(self.opt.get("stDevWicketRate", [3.96, 0.92, 2.24, 4.5, 21]))
        runRateSize = (len(stDevRunRate) if len(meanRunRate) > len(stDevRunRate)
                       else len(meanRunRate))
        wicketRateSize = (len(stDevWicketRate) if len(meanWicketRate) > len(stDevWicketRate)
                          else len(meanWicketRate))

        # if the home and away skill are both 0, we can’t calculate the ratio,
        # and use 0.5 instead
        skillRatio = (0.5 if home.rpSkill == away.rpSkill
                      else home.rpSkill / (home.rpSkill + away.rpSkill))
        homeSkill = skillCoeff * skillRatio + skillOffset + homeAdvantage
        awaySkill = 1 - homeSkill

        homeGetsStyleEffect = (self.s.randUniform() < homeSkill)
        homeBatsFirst = (self.s.randUniform() < 0.5)

        homeRunRateModifier = int(self.s.randUniform() * (runRateSize - 1)
                                  + (1 if self.s.randUniform() < homeSkill else 0))
        awayRunRateModifier = int(self.s.randUniform() * (runRateSize - 1)
                                  + (1 if self.s.randUniform() < awaySkill else 0))
        homeWicketRateModifier = int(self.s.randUniform() * (wicketRateSize - 1)
                                     + 1 - (1 if self.s.randUniform() < awaySkill else 0))
        awayWicketRateModifier = int(self.s.randUniform() * (wicketRateSize - 1)
                                     + 1 - (1 if self.s.randUniform() < homeSkill else 0))

        homeRunRate = (self.s.randGaussian() * toDouble(stDevRunRate[homeRunRateModifier])
                       + toDouble(meanRunRate[homeRunRateModifier]))
        awayRunRate = (self.s.randGaussian() * toDouble(stDevRunRate[awayRunRateModifier])
                       + toDouble(meanRunRate[awayRunRateModifier]))
        homeWicketRate = (self.s.randGaussian() * toDouble(stDevWicketRate[homeWicketRateModifier])
                          + toDouble(meanWicketRate[homeWicketRateModifier]))
        awayWicketRate = (self.s.randGaussian() * toDouble(stDevWicketRate[awayWicketRateModifier])
                          + toDouble(meanWicketRate[awayWicketRateModifier]))

        if useStyleMods:
            homeStyleValue = (toDouble(home.property("style")) + 5) / 2
            awayStyleValue = (toDouble(away.property("style")) + 5) / 2

            if homeGetsStyleEffect:
                homeRunRate *= 1 + styleCoeff * homeStyleValue
                homeWicketRate *= 1 + styleCoeff * (5 - awayStyleValue)
            else:
                awayRunRate *= 1 + styleCoeff * awayStyleValue
                awayWicketRate *= 1 + styleCoeff * (5 - homeStyleValue)

        baseHomeRuns = homeRunRate * maxOvers
        baseAwayRuns = awayRunRate * maxOvers
        homeWickets = maxBalls / homeWicketRate
        awayWickets = maxBalls / awayWicketRate

        homeRuns = float(int(baseHomeRuns * (maxWickets / homeWickets if homeWickets > maxWickets else 1)))
        awayRuns = float(int(baseAwayRuns * (maxWickets / awayWickets if awayWickets > maxWickets else 1)))
        homeWickets = float(int(homeWickets if homeWickets < maxWickets else maxWickets))
        awayWickets = float(int(awayWickets if awayWickets < maxWickets else maxWickets))

        # if the team batting second won, they couldn’t have won by many runs
        winningRuns = int(self.s.randUniform() * 4 + 1)
        if homeBatsFirst and awayRuns > homeRuns + winningRuns:
            awayRuns = homeRuns + winningRuns
        elif not homeBatsFirst and homeRuns > awayRuns + winningRuns:
            homeRuns = awayRuns + winningRuns

        # if the team batting second won, they couldn’t have been all out
        if homeBatsFirst and awayRuns > homeRuns and awayWickets > maxWickets - 1:
            awayWickets = maxWickets - 1
        elif not homeBatsFirst and homeRuns > awayRuns and homeWickets > maxWickets - 1:
            homeWickets = maxWickets - 1

        homeBalls = maxBalls
        awayBalls = maxBalls
        if homeWickets == maxWickets or (not homeBatsFirst and homeRuns > awayRuns):
            homeBalls = int(homeBalls * (homeRuns / baseHomeRuns))
        if awayWickets == maxWickets or (homeBatsFirst and awayRuns > homeRuns):
            awayBalls = int(awayBalls * (awayRuns / baseAwayRuns))

        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        hRes.setScore(homeRuns)
        aRes.setScore(awayRuns)
        hRes.result["wickets"] = homeWickets
        aRes.result["wickets"] = awayWickets
        hRes.result["balls"] = homeBalls
        aRes.result["balls"] = awayBalls

        return (hRes, aRes)

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        return -1  # we don’t use this

    def outputLine(self, res, away=None):
        # collapses the C++ overloads outputLine(XkorResult) and
        # outputLine(XkorResult, XkorResult)
        if away is not None:
            return self.outputLine(res) + "\n" + self.outputLine(away) + "\n"

        maxWickets = toInt(self.opt.get("maxWickets", 10))
        ballsPerOver = toInt(self.opt.get("ballsPerOver", 6))

        rval = res.athlete.name + " "
        rval += qNumber(res.score())
        if toInt(res.value("wickets")) < maxWickets:
            rval += "/" + toString(res.value("wickets"))
        balls = toInt(res.value("balls"))
        if balls % ballsPerOver == 0:
            rval += " (" + str(balls // ballsPerOver) + " overs)"
        else:
            rval += " (" + str(balls // ballsPerOver) + "." + str(balls % ballsPerOver) + " overs)"
        return rval
