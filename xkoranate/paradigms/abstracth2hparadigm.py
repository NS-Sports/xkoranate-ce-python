import math
import sys

from ..result import XkorResult
from ..variant import qNumber, toDouble, toInt, toList, toString
from .abstractparadigm import XkorAbstractParadigm
from .comparators.h2hresultcomparator import XkorH2HResultComparator

INT_MAX = 2147483647  # numeric_limits<int>::max()


class XkorAbstractH2HParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["matches"] = True
        self.supportedCompetitions["roundRobin"] = True
        self.supportedCompetitions["singleElimination"] = True

    def breakTie(self, athletes, type=""):
        acc = 0

        tiebreakers = self.readOptionList("tiebreakers")
        tiebreakerNames = self.readOptionList("tiebreakerNames")

        for awayIdx in range(len(athletes)):
            if acc & 1:
                away = athletes[awayIdx]
                home = athletes[awayIdx - 1]  # home = away - 1

                score1 = self.findResult(home.id)
                score2 = self.findResult(away.id)

                ni = 0  # parallel iterator over tiebreakerNames
                ti = 0
                while ti < len(tiebreakers):
                    tbType = toString(tiebreakers[ti])
                    name = toString(tiebreakerNames[ni])
                    if tbType == "decision":
                        score = self.generateDecisionScore(score1, score2, name)
                    elif tbType == "extratime":
                        score = self.generateETScore(score1, score2, name)
                    elif tbType == "goldengoal":
                        score = self.generateGGScore(score1, score2, name)
                    elif tbType == "ifaf":
                        score = self.generateIFAFScore(score1, score2, name,
                                                       toInt(score1.result.get("OTs")) + 1)
                    elif tbType == "shootout":
                        score = self.generateSOScore(score1, score2, name)
                    else:
                        print("bad tiebreaker", tbType, file=sys.stderr)
                        # C++ leaves the QPair default-constructed (two empty
                        # results) in this case
                        score = (XkorResult(), XkorResult())

                    # output the score
                    for j in range(len(self.out)):
                        if self.out[j][0] == home.name:
                            self.out[j] = (self.out[j][0],
                                           self.outputLine(score[0], score[1]))

                    # let the competition know the result
                    # (C++: *score1 = score.first; *score2 = score.second —
                    # overwrite the stored results in place)
                    score1.athlete = score[0].athlete
                    score1.result = score[0].result
                    score2.athlete = score[1].athlete
                    score2.result = score[1].result

                    # keep track of the number of overtimes under IFAF rules
                    if tbType == "ifaf":
                        score1.result["OTs"] = toInt(score1.result.get("OTs")) + 1
                        score2.result["OTs"] = toInt(score2.result.get("OTs")) + 1

                    # are we done?
                    if self.compare(score[0], score[1]) != 0:
                        break

                    # are we on the last tiebreaker? if so, let’s do it again
                    if ti + 1 == len(tiebreakers):
                        ti -= 1
                        ni -= 1

                    ni += 1
                    ti += 1
            acc += 1

    def comparisonFunction(self, type=""):
        return XkorH2HResultComparator(type, self.opt)

    def estimateOdds(self, home, away, trials=1000):
        """Monte Carlo estimate of regular-time win/draw/loss probabilities
        for a specific home/away pairing. Runs on an isolated PRNG so this
        never perturbs the sequence used for real scorination."""
        from ..rng import Mt19937
        from ..sport import XkorSport

        simSport = XkorSport()
        simSport.m_paradigmOptions = dict(self.s.m_paradigmOptions)
        simSport.m_dataPoints = {k: dict(v) for k, v in self.s.m_dataPoints.items()}
        simSport.r = Mt19937()
        simParadigm = type(self)(simSport, self.userOpt)

        wins = draws = losses = 0
        for _ in range(trials):
            homeResult, awayResult = simParadigm.generateFTScore(home, away)
            if homeResult.score() > awayResult.score():
                wins += 1
            elif homeResult.score() < awayResult.score():
                losses += 1
            else:
                draws += 1

        return {"win": wins / trials, "draw": draws / trials, "loss": losses / trials}

    def newAthleteWidget(self):
        if (toString(self.userOpt.get("styleMods")) != "false"
                or toString(self.userOpt.get("NSFSStyleMods")) != "false"):
            from ..signuplisteditor.athletewidget import XkorAthleteWidget
            return XkorAthleteWidget(["name", "nation", "skill", "style"],
                                     ["Participant", "Team", "Skill", "Style"],
                                     ["string", "string", "skill", "double"],
                                     -5, 5, 1)
        else:
            return super().newAthleteWidget()

    def scorinate(self, athletes, previousResults=None):
        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i,
                      "in XkorAbstractH2HParadigm::output(XkorResults *)",
                      file=sys.stderr)
                self.out.append(("", "Sport does not support this paradigm"))
                return

        # initialize results
        self.out = []
        self.res = []

        acc = 0
        for awayIdx in range(len(athletes)):
            if acc & 1:  # if we’re on the second team in a match
                away = athletes[awayIdx]
                home = athletes[awayIdx - 1]  # home = away - 1

                score = self.generateFTScore(home, away)

                status = ""
                if self.compare(score[0], score[1]) == 0:
                    status = self.generateStatus()

                if status != "" and self.compare(score[0], score[1]) == -1:
                    score[1].result["status"] = status
                elif status != "":
                    score[0].result["status"] = status

                # output the FT score
                self.out.append((home.name, self.outputLine(score[0], score[1])))
                self.res.append(score[0])
                self.res.append(score[1])

                if (self.compare(score[0], score[1]) == 0
                        and toInt(self.opt.get("forceTieBreak")) == 1):
                    # tiebreakers are required for this sport
                    self.breakTie([home, away])
            acc += 1

    # protected:

    def formatGaelicScore(self, subScores, totalScore):
        # collapses the C++ overloads formatGaelicScore(QList<QVariant>, int)
        # and formatGaelicScore(XkorResult, XkorResult)
        if isinstance(subScores, XkorResult):
            return self._formatGaelicScoreResults(subScores, totalScore)
        result = ""
        if toString(self.opt.get("resultStyle")) == "australian":
            for i in range(len(subScores)):
                if i > 0:
                    result += "."
                result += str(toInt(subScores[i]))
            result += "." + str(totalScore)
        else:  # gaelic
            for i in range(len(subScores)):
                if i > 0:
                    result += "-"
                result += str(toInt(subScores[i]))
            result += " (" + str(totalScore) + ")"
        return result

    def _formatGaelicScoreResults(self, score1, score2):
        rval = (self.formatName(score1.athlete) + " "
                + self.formatGaelicScore(toList(score1.value("subScores")),
                                         int(score1.score())))
        if score1.score() > score2.score():
            rval += " def. "
        elif score1.score() == score2.score():
            rval += " drew with "
        else:
            rval += " def. by "
        rval += (self.formatName(score2.athlete) + " "
                 + self.formatGaelicScore(toList(score2.value("subScores")),
                                          int(score2.score())))

        # extra time and stuff
        usedTiebreakers = []
        tiebreakers = self.readOptionList("tiebreakers")
        tiebreakerNames = self.readOptionList("tiebreakerNames")
        for i in range(len(tiebreakerNames)):
            name = toString(tiebreakerNames[i])
            if (name not in usedTiebreakers
                    and (score1.value(name) is not None or score2.value(name) is not None)):
                rval += (" ("
                         + self.formatGaelicScore(toList(score1.value(name)),
                                                  int(toDouble(score1.value(name + "SubScores"))))
                         + " – "
                         + self.formatGaelicScore(toList(score2.value(name)),
                                                  int(toDouble(score2.value(name + "SubScores"))))
                         + ")")
            usedTiebreakers.append(name)
        return rval

    def formatPeriodScore(self, score1, score2):
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth"))
        periods = toInt(self.opt.get("periods"))

        homeScore = self.formatName(score1.athlete).ljust(nameWidth)
        awayScore = self.formatName(score2.athlete).ljust(nameWidth)

        subScores1 = toList(score1.value("subScores"))
        subScores2 = toList(score2.value("subScores"))
        i = 0
        while i < len(subScores1) or i < len(subScores2) or i < periods:
            if i < len(subScores1):
                homeSubScore = toString(subScores1[i]).rjust(resultWidth)
            else:
                homeSubScore = "X".rjust(resultWidth)
            if i < len(subScores2):
                awaySubScore = toString(subScores2[i]).rjust(resultWidth)
            else:
                awaySubScore = "X".rjust(resultWidth)

            # if we have a result that’s too long, pad the other one to match
            if len(homeSubScore) > resultWidth:
                awaySubScore = awaySubScore.rjust(len(homeSubScore))
            if len(awaySubScore) > resultWidth:
                homeSubScore = homeSubScore.rjust(len(awaySubScore))

            homeScore += " " + homeSubScore
            awayScore += " " + awaySubScore
            i += 1

        homeTotal = score1.score()
        awayTotal = score2.score()

        # overtime and stuff
        usedTiebreakers = []
        tiebreakers = self.readOptionList("tiebreakers")
        tiebreakerNames = self.readOptionList("tiebreakerNames")
        for i in range(len(tiebreakerNames)):
            name = toString(tiebreakerNames[i])
            if (name not in usedTiebreakers
                    and (score1.value(name) is not None or score2.value(name) is not None)):
                if score1.contains(name):
                    homeScore += toString(score1.value(name)).rjust(resultWidth)
                else:
                    homeScore += "X".rjust(resultWidth)
                if score2.contains(name):
                    awayScore += toString(score2.value(name)).rjust(resultWidth)
                else:
                    awayScore += "X".rjust(resultWidth)
                homeTotal += toDouble(score1.value(name))
                awayTotal += toDouble(score2.value(name))
            usedTiebreakers.append(name)

        homeScore += qNumber(homeTotal).rjust(resultWidth + 2)
        awayScore += qNumber(awayTotal).rjust(resultWidth + 2)

        return homeScore + "\n" + awayScore + "\n"

    def formatScore(self, score1, score2):
        # collapses the C++ overloads formatScore(double, double) and
        # formatScore(XkorResult, XkorResult)
        if isinstance(score1, XkorResult):
            return self._formatScoreResults(score1, score2)
        return qNumber(score1) + "–" + qNumber(score2)

    def _formatScoreResults(self, score1, score2):
        rval = (self.formatName(score1.athlete) + " "
                + self.formatScore(score1.score(), score2.score()) + " "
                + self.formatName(score2.athlete))

        # extra time and stuff
        usedTiebreakers = []
        tiebreakers = self.readOptionList("tiebreakers")
        tiebreakerNames = self.readOptionList("tiebreakerNames")
        for i in range(len(tiebreakerNames)):
            name = toString(tiebreakerNames[i])
            if (name not in usedTiebreakers
                    and (score1.value(name) is not None or score2.value(name) is not None)):
                if toString(tiebreakers[i]) == "shootout":
                    rval += (" (" + self.formatScore(toDouble(score1.value(name)),
                                                     toDouble(score2.value(name)))
                             + " " + name + ")")
                else:
                    rval += (" (" + self.formatScore(score1.score() + toDouble(score1.value(name)),
                                                     score2.score() + toDouble(score2.value(name)))
                             + " " + name + ")")
            usedTiebreakers.append(name)

        return rval

    def generateConversions(self, count, forceValue=-1):
        rval = 0

        conversionValues = self.readOptionList("conversionValues")
        conversionSelection = self.readOptionList("conversionSelection")
        conversionSuccess = self.readOptionList("conversionSuccess")

        i = 0
        while i < count:
            rand = self.s.randUniform()
            selectionIdx = 0
            # the total probability of us selecting any of the conversion
            # types we’ve tried so far
            selectionAcc = toDouble(conversionSelection[selectionIdx])
            conversionIndex = 0
            for j in conversionValues:
                if forceValue == conversionIndex or (forceValue < 0 and rand < selectionAcc):
                    if self.s.randUniform() < toDouble(conversionSuccess[conversionIndex]):
                        rval += toInt(j)  # conversion successful!
                    break

                selectionIdx += 1
                selectionAcc += toDouble(conversionSelection[selectionIdx])
                conversionIndex += 1
            i += 1

        return rval

    def generateDecisionScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        homeScore = self.s.randWeightedH2H(home.athlete.rpSkill, away.athlete.rpSkill) * INT_MAX
        awayScore = self.s.randWeightedH2H(away.athlete.rpSkill, home.athlete.rpSkill) * INT_MAX
        if homeScore > awayScore:
            home.result["decision"] = str_
        else:
            away.result["decision"] = str_
        return (home, away)

    def generateETScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        attackMultiplier = toDouble(self.opt.get("etAttackCoeff"))
        homeAdvantage = (toString(self.userOpt.get("homeAdvantage")) == "true")
        pointValues = self.readOptionList("pointValues")
        attackCoeffs = self.readOptionList("attackCoeffs")

        scoreType = ("score" if str_ == "" else str_)
        subScoreType = ("subScores" if str_ == "" else str_ + "SubScores")

        for i in range(len(pointValues)):  # for each type of scoring
            attackCoeff = toDouble(attackCoeffs[i])
            score1 = self.generateScore(home.athlete.rpSkill, away.athlete.rpSkill,
                                        0, 0, homeAdvantage, attackCoeff * attackMultiplier)
            score2 = self.generateScore(away.athlete.rpSkill, home.athlete.rpSkill,
                                        0, 0, False, attackCoeff * attackMultiplier)

            # add to overall score
            home.result[scoreType] = toDouble(home.value(scoreType)) + score1 * toInt(pointValues[i])
            away.result[scoreType] = toDouble(away.value(scoreType)) + score2 * toInt(pointValues[i])

            # store the sub-score
            homeScores = toList(home.result.get(subScoreType))
            awayScores = toList(away.result.get(subScoreType))
            homeScores.append(score1)
            awayScores.append(score2)
            home.result[subScoreType] = homeScores
            away.result[subScoreType] = awayScores

            if i == 0 and self.opt.get("conversionValues") is not None:
                home.result[scoreType] = toDouble(home.value(scoreType)) + self.generateConversions(score1)
                away.result[scoreType] = toDouble(away.value(scoreType)) + self.generateConversions(score2)

        return (home, away)

    def generateFTScore(self, home, away):
        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        homeAdvantage = (toString(self.userOpt.get("homeAdvantage")) == "true")
        pointValues = self.readOptionList("pointValues")
        attackCoeffs = self.readOptionList("attackCoeffs")

        for i in range(len(pointValues)):  # for each type of scoring
            attackCoeff = toDouble(attackCoeffs[i])
            # zero out the styles because we use our own system
            score1 = self.generateScore(home.rpSkill, away.rpSkill, 0, 0,
                                        homeAdvantage, attackCoeff)
            score2 = self.generateScore(away.rpSkill, home.rpSkill, 0, 0,
                                        False, attackCoeff)

            # calculate style effect
            if (self.s.hasValue("style")
                    and (toString(self.userOpt.get("styleMods")) != "false"
                         or toString(self.userOpt.get("NSFSStyleMods")) != "false")):  # on by default
                styleResults = self.generateStyleModification(
                    score1, score2,
                    toDouble(home.property("style")), toDouble(away.property("style")))
                score1 = styleResults[0]
                score2 = styleResults[1]

            # add to overall score
            hRes.setScore(hRes.score() + score1 * toInt(pointValues[i]))
            aRes.setScore(aRes.score() + score2 * toInt(pointValues[i]))

            # store the sub-score
            hResScores = toList(hRes.result.get("subScores"))
            aResScores = toList(aRes.result.get("subScores"))
            hResScores.append(score1)
            aResScores.append(score2)
            hRes.result["subScores"] = hResScores
            aRes.result["subScores"] = aResScores

            if i == 0 and self.opt.get("conversionValues") is not None:
                hRes.setScore(hRes.score() + self.generateConversions(score1))
                aRes.setScore(aRes.score() + self.generateConversions(score2))

        return (hRes, aRes)

    def generateGGScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        goldenGoalProb = toDouble(self.opt.get("goldenGoalProb"))
        homeAdvantage = toDouble(self.opt.get("homeAdvantageGG"))

        scoreType = ("score" if str_ == "" else str_)

        if self.s.randUniform() < goldenGoalProb:  # someone scored; who was it?
            # what type of score?
            scoreValue = 1
            ggPointProbs = self.readOptionList("goldenGoalPointProbs")
            pointValues = self.readOptionList("pointValues")
            # C++: if(ggPointProbs == QVariant()) — in Qt4 a List variant never
            # compares equal to an invalid QVariant, so this branch is dead
            # code; preserved here for fidelity
            if False:
                scoreValue = toInt(pointValues[0])
            else:
                rand = self.s.randUniform()
                probAcc = 0.0
                currentValue = 0
                for i in ggPointProbs:
                    probAcc += toDouble(i)
                    if rand < probAcc:
                        scoreValue = toInt(pointValues[currentValue])
                        break
                    currentValue += 1

            homeSkill = home.athlete.rpSkill
            awaySkill = away.athlete.rpSkill
            if toString(self.userOpt.get("homeAdvantage")) == "true":
                homeSkill = homeSkill * (1 - homeAdvantage) + homeAdvantage
                awaySkill = awaySkill * (1 - homeAdvantage)
            otScore1 = self.s.randWeightedH2H(homeSkill, awaySkill)
            otScore2 = self.s.randWeightedH2H(awaySkill, homeSkill)

            if otScore1 > otScore2:
                home.result[scoreType] = toDouble(home.result.get(scoreType)) + scoreValue
            else:
                away.result[scoreType] = toDouble(away.result.get(scoreType)) + scoreValue
        return (home, away)

    def generateIFAFScore(self, home, away, str_, otNumber):
        home = home.clone()
        away = away.clone()

        # what type of score?
        firstScore = 0
        secondScore = 0
        ifafPointProbs = self.readOptionList("ifafPointProbs")
        pointValues = self.readOptionList("pointValues")

        # coin flip to decide which team went first
        # theoretically this should be done only once, but it doesn’t matter
        homeTeamWentFirst = (self.s.randUniform() > 0.5)
        if homeTeamWentFirst:
            firstTeam = home
            secondTeam = away
        else:
            firstTeam = away
            secondTeam = home

        # scorinate random numbers
        homeAdvantage = toDouble(self.opt.get("homeAdvantageIFAF"))
        firstSkill = firstTeam.athlete.rpSkill
        secondSkill = secondTeam.athlete.rpSkill
        if homeAdvantage:
            firstSkill = firstSkill * (1 - homeAdvantage) + homeAdvantage
            secondSkill = secondSkill * (1 - homeAdvantage)
        randFirst = self.s.randWeightedH2H(firstSkill, secondSkill)
        randSecond = self.s.randWeightedH2H(secondSkill, firstSkill)

        currentValue = 0
        canHaveConversion = True  # only the first value can have a conversion
        probAcc = 0.0
        for i in ifafPointProbs:
            probAcc += toDouble(i)

            if firstScore == 0 and randFirst < probAcc:
                firstScore = toInt(pointValues[currentValue])
            if secondScore == 0 and randSecond < probAcc:
                secondScore = toInt(pointValues[currentValue])
            if canHaveConversion:
                if firstScore > 0:
                    if otNumber >= 3:
                        firstScore += self.generateConversions(1, 1)
                    else:
                        firstScore += self.generateConversions(1)
                if secondScore > 0:
                    if otNumber >= 3:
                        secondScore += self.generateConversions(1, 1)
                    elif firstScore == secondScore:
                        # get the easiest conversion possible if we’re tied
                        secondScore += self.generateConversions(1, 0)
                    elif firstScore > secondScore:
                        secondScore += self.generateConversions(1)
            if firstScore > 0:
                # if the team that went first scored a touchdown, their
                # opponent won’t bother attempting a field goal
                break
            currentValue += 1
            canHaveConversion = False

        firstTeam.result[str_] = toDouble(firstTeam.value(str_)) + firstScore
        secondTeam.result[str_] = toDouble(secondTeam.value(str_)) + secondScore

        return (home, away)

    def generateSOScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()
        pkCount = toInt(self.opt.get("shootoutLength"))
        pkProb = toDouble(self.opt.get("shootoutProb"))

        count = 0
        while abs(toInt(home.value(str_)) - toInt(away.value(str_))) <= pkCount - count:
            if self.s.randUniform() < pkProb:
                home.result[str_] = toInt(home.value(str_)) + 1
            if self.s.randUniform() < pkProb:
                away.result[str_] = toInt(away.value(str_)) + 1
            if count >= pkCount:
                count -= 1
            count += 1

        return (home, away)

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        raise NotImplementedError

    def generateStyleModification(self, homeScore, awayScore, homeStyle, awayStyle):
        if toString(self.userOpt.get("NSFSStyleMods")) == "true":
            styleCoeffA = toDouble(self.opt.get("NSFSStyleCoeffA", 2.0991677816057))
            styleCoeffB = toDouble(self.opt.get("NSFSStyleCoeffB", 1.2442581729602))
            styleExponent = toDouble(self.opt.get("NSFSStyleExponent", -0.42705203296846))
            styleOffset = toDouble(self.opt.get("NSFSStyleOffset", 0.072435335725325))

            styleModifier = (homeStyle + awayStyle) / 2.0 + self.s.randGaussian()
            result = homeScore - awayScore

            styleMultiplier = (styleCoeffA
                               / (1 + styleCoeffB * math.pow(math.e, styleExponent * styleModifier))
                               + styleOffset)

            homeScore = int(homeScore * styleMultiplier)
            awayScore = int(awayScore * styleMultiplier)

            # if a negative style modifier changed the result to a draw, fix it
            if homeScore == awayScore and result > 0:
                homeScore += 1
            elif homeScore == awayScore and result < 0:
                awayScore += 1

            return (homeScore, awayScore)
        else:
            styleEffect = 0
            # what’s the maximum change we can make that will preserve W/D/L?
            maxStyleEffect = ((0 if homeScore == awayScore else abs(homeScore - awayScore) - 1)
                              + min(homeScore, awayScore))
            styleEffect = int(self.s.individualScore("style", (homeStyle + awayStyle) / 20 + 0.5))
            if styleEffect < -maxStyleEffect:
                styleEffect = -maxStyleEffect
            homeScore += max(-homeScore, styleEffect)  # don’t drop the score below 0
            awayScore += max(-awayScore, styleEffect)  # don’t drop the score below 0
            return (homeScore, awayScore)

    def generateStatus(self):
        statuses = self.readOptionList("statuses")
        statusProbs = self.readOptionList("statusProbs")

        rand = self.s.randUniform()

        acc = 0.0
        for i in range(len(statuses)):
            acc += toDouble(statusProbs[i])
            if rand < acc:
                return toString(statuses[i])
        return ""

    def outputLine(self, home, away=None):
        # collapses the C++ overloads outputLine(XkorResult) (inherited) and
        # outputLine(XkorResult, XkorResult)
        if away is None:
            return super().outputLine(home)
        if toString(home.value("status")) != "":
            rval = (self.formatName(home.athlete) + " def. by " + self.formatName(away.athlete)
                    + " (" + toString(home.value("status")) + ")")
        elif toString(away.value("status")) != "":
            rval = (self.formatName(home.athlete) + " def. " + self.formatName(away.athlete)
                    + " (" + toString(away.value("status")) + ")")
        elif home.value("decision") is not None:
            rval = (self.formatName(home.athlete) + " " + toString(home.value("decision"))
                    + self.formatScore(home.score(), away.score()) + " "
                    + self.formatName(away.athlete))
        elif away.value("decision") is not None:
            rval = (self.formatName(home.athlete) + " "
                    + self.formatScore(home.score(), away.score())
                    + toString(away.value("decision")) + " " + self.formatName(away.athlete))
        elif (toString(self.opt.get("resultStyle")) == "periods"
                and toString(self.userOpt.get("usePeriods", "true")) == "true"):
            rval = self.formatPeriodScore(home, away)
        elif (toString(self.opt.get("resultStyle")) == "australian"
                or toString(self.opt.get("resultStyle")) == "gaelic"):
            rval = self.formatGaelicScore(home, away)
        else:
            rval = self.formatScore(home, away)
        return rval
