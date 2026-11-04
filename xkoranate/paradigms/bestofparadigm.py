import sys

from ..result import XkorResult
from ..variant import toInt
from .abstractparadigm import XkorAbstractParadigm
from .pointbypoint import XkorPointByPointMixin


class XkorBestOfParadigm(XkorPointByPointMixin, XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["matches"] = True
        self.supportedCompetitions["roundRobin"] = True

    def breakTie(self, athletes, type=""):
        print("unexpected tie break request in best of paradigm", file=sys.stderr)

    def scorinate(self, athletes, previousResults=None):
        if not self._checkRequiredValues("XkorBestOfParadigm::output(XkorResults *)"):
            return

        # initialize results
        self.out = []
        self.res = []

        for home, away in self._pairs(athletes):
            games = toInt(self.opt.get("games"))

            score = [0, 0]
            while score[0] <= games // 2 and score[1] <= games // 2:
                # each game is won like a single point
                currentGameScore = self.generatePointScore(home.rpSkill, away.rpSkill)

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

    # protected:

    def individualResult(self, a, b, c=None):
        return XkorResult()  # unused
