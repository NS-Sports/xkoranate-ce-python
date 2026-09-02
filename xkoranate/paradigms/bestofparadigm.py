import sys

from ..result import XkorResult
from ..variant import toDouble, toInt
from .abstractparadigm import XkorAbstractParadigm


class XkorBestOfParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["matches"] = True
        self.supportedCompetitions["roundRobin"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in best of paradigm", file=sys.stderr)

    def hasOptionsWidget(self):
        return True

    def newOptionsWidget(self, paradigmOptions):
        from .options.timedparadigmoptions import XkorTimedParadigmOptions
        return XkorTimedParadigmOptions(paradigmOptions)

    def scorinate(self, athletes, previousResults=None):
        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i,
                      "in XkorBestOfParadigm::output(XkorResults *)",
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

                games = toInt(self.opt.get("games"))

                score = [0, 0]
                while score[0] <= games // 2 and score[1] <= games // 2:
                    currentGameScore = self.generateGameScore(home.rpSkill, away.rpSkill)

                    if currentGameScore[0] > currentGameScore[1]:
                        score[0] += 1
                    else:
                        score[1] += 1

                if games > 1:
                    result = (self.formatName(home.name, home.nation) + " "
                              + self.formatScore(score[0], score[1]) + " "
                              + self.formatName(away.name, away.nation))
                elif score[0] > score[1]:  # if there’s only one game, show “def.”/“def. by”
                    result = (self.formatName(home.name, home.nation) + " def. "
                              + self.formatName(away.name, away.nation))
                else:
                    result = (self.formatName(home.name, home.nation) + " def. by "
                              + self.formatName(away.name, away.nation))

                self.out.append((home.name, result))
                self.res.append(XkorResult(score[0], ath=home.clone()))
                self.res.append(XkorResult(score[1], ath=away.clone()))
            acc += 1

    # protected:

    def individualResult(self, a, b, c=None):
        return XkorResult()  # unused

    def formatScore(self, score1, score2):
        return str(score1) + "–" + str(score2)

    def generateGameScore(self, homeSkill, awaySkill):
        attackModifier = toDouble(self.opt.get("attackModifier"))

        first = self.s.randWeightedH2H(homeSkill, awaySkill) + self.s.randUniform() * attackModifier
        second = self.s.randWeightedH2H(awaySkill, homeSkill) + self.s.randUniform() * attackModifier

        return (first, second)
