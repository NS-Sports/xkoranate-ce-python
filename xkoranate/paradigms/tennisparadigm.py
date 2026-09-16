import sys

from ..result import XkorResult
from ..variant import toDouble, toInt
from .abstractparadigm import XkorAbstractParadigm

INT_MAX = 2147483647  # numeric_limits<int>::max()


class XkorTennisParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["matches"] = True
        self.supportedCompetitions["roundRobin"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in tennis paradigm", file=sys.stderr)

    def hasOptionsWidget(self):
        return True

    def newOptionsWidget(self, paradigmOptions):
        from .options.timedparadigmoptions import XkorTimedParadigmOptions
        return XkorTimedParadigmOptions(paradigmOptions)

    def scorinate(self, athletes, previousResults=None):
        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i,
                      "in XkorSQISParadigm::output(XkorResults *)",
                      file=sys.stderr)
                self.out.append(("", "Sport does not support this paradigm"))
                return

        # load options
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 2)) + 2

        # initialize results
        self.out = []
        self.res = []

        acc = 0
        for awayIdx in range(len(athletes)):
            if acc & 1:  # if we’re on the second team in a match
                away = athletes[awayIdx]
                home = athletes[awayIdx - 1]  # home = away - 1

                sets = toInt(self.opt.get("sets"))

                score = (0, 0)
                setScores = []
                i = 0
                while score[0] <= sets // 2 and score[1] <= sets // 2:
                    isFinalSet = (i == sets - 1)
                    currentSetScore = self.generateSetScore(home.rpSkill, away.rpSkill,
                                                            isFinalSet)
                    setScores.append(currentSetScore)

                    if sets > 1:
                        if currentSetScore[0] > currentSetScore[1]:
                            score = (score[0] + 1, score[1])
                        else:
                            score = (score[0], score[1] + 1)
                    else:
                        score = currentSetScore
                    i += 1

                # output the home score
                homeResult = self.formatName(home).ljust(nameWidth)
                for i in setScores:
                    homeResult += str(i[0]).rjust(resultWidth)
                self.out.append((home.name, homeResult))
                self.res.append(XkorResult(score[0], ath=home.clone()))

                # output the away score
                awayResult = self.formatName(away).ljust(nameWidth)
                for i in setScores:
                    awayResult += str(i[1]).rjust(resultWidth)
                awayResult += "\n"
                self.out.append((away.name, awayResult))
                self.res.append(XkorResult(score[1], ath=away.clone()))
            acc += 1

    # protected:

    def individualResult(self, a, b, c=None):
        return ("", 0.0)  # unused (C++ returns QPair<QString, double>())

    def generateSetScore(self, homeSkill, awaySkill, isFinalSet):
        rval = (0, 0)

        attackModifier = toDouble(self.opt.get("attackModifier"))
        # determine how many points we’re playing to and so forth
        if isFinalSet:
            winPoints = toInt(self.opt.get("finalSetWinPoints"))
            winMargin = toInt(self.opt.get("finalSetWinMargin"))
            endPoints = toInt(self.opt.get("finalSetEndPoints"))
        else:
            winPoints = toInt(self.opt.get("winPoints"))
            winMargin = toInt(self.opt.get("winMargin"))
            endPoints = toInt(self.opt.get("endPoints"))

        if endPoints == 0:
            # if endPoints is set to 0, play until a two-point lead or the
            # computer explodes!
            endPoints = INT_MAX

        # …until someone wins, play points
        while (rval[0] < endPoints and rval[1] < endPoints
               and (rval[0] < winPoints or rval[0] - rval[1] < winMargin)
               and (rval[1] < winPoints or rval[1] - rval[0] < winMargin)):
            homeRand = (self.s.randWeightedH2H(homeSkill, awaySkill)
                        + self.s.randUniform() * attackModifier)
            awayRand = (self.s.randWeightedH2H(awaySkill, homeSkill)
                        + self.s.randUniform() * attackModifier)
            if homeRand > awayRand:
                rval = (rval[0] + 1, rval[1])
            else:
                rval = (rval[0], rval[1] + 1)

        return rval
