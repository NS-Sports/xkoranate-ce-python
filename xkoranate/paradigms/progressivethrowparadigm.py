import sys

from ..result import XkorResult
from ..variant import toInt, toList, toString
from .scoredparadigm import XkorScoredParadigm


class XkorProgressiveThrowParadigm(XkorScoredParadigm):
    # protected:

    def scorinate(self, athletes, previousResults=None):
        if previousResults is None:
            previousResults = []

        # check that we can use the sport
        if not self._checkRequiredValues("XkorProgressiveThrowParadigm::scorinate(QList<XkorAthlete>)"):
            return

        # initialize results
        self.out = []
        self.res = []

        for i in athletes:
            r = XkorResult()
            r.athlete = i.clone()

            # load up the previous result, if any
            for j in previousResults:
                if j.athlete == i:
                    self._extendAttempts(r, j)

            priorAttempts = len(toList(r.result.get("attempts")))
            for j in range(priorAttempts, priorAttempts + toInt(self.opt.get("attempts", 1))):
                result = self.individualResult(i, "attempts")
                accuracyResult = self.individualResult(i, "accuracy", "accuracy")
                result.setScoreString(str(int(accuracyResult.score() * result.score()))
                                      + "/" + result.scoreString())
                result.setScore(int(accuracyResult.score() * result.score()))
                self._appendAttempt(r, result.score(), result.scoreString())
                if (toString(self.opt.get("totalType")) != "best"
                        and (result.score() == sys.float_info.max
                             or result.score() == -sys.float_info.max)):
                    break
            self.calculateTotal(r)

            self.res.append(r)

        self.generateOutput()
