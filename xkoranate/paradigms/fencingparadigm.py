import sys

from ..result import XkorResult
from ..variant import toDouble, toInt
from .abstractparadigm import XkorAbstractParadigm
from .pointbypoint import XkorPointByPointMixin


class XkorFencingParadigm(XkorPointByPointMixin, XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["matches"] = True
        self.supportedCompetitions["roundRobin"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in fencing paradigm", file=sys.stderr)

    def scorinate(self, athletes, previousResults=None):
        if not self._checkRequiredValues("XkorFencingParadigm::output(XkorResults *)"):
            return

        # initialize results
        self.out = []
        self.res = []

        for home, away in self._pairs(athletes):
            matchLength = toDouble(self.opt.get("matchLength"))
            winPoints = toInt(self.opt.get("winPoints"))

            # calculate number of points
            pointsRate = self.s.individualScore("pointRate")
            pointsPlayed = int(matchLength / pointsRate)

            score = [0, 0]
            while (score[0] < winPoints and score[1] < winPoints
                   and (score[0] + score[1] < pointsPlayed or score[0] == score[1])):
                currentPointScore = self.generatePointScore(home.rpSkill, away.rpSkill)

                if currentPointScore[0] > currentPointScore[1]:
                    score[0] += 1
                else:
                    score[1] += 1

            result = (self.formatName(home.name, home.nation) + " "
                      + self.formatScore(score[0], score[1]) + " "
                      + self.formatName(away.name, away.nation))

            self.out.append((home.name, result))
            self.res.append(XkorResult(score[0], ath=home.clone()))
            self.res.append(XkorResult(score[1], ath=away.clone()))

