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
        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i,
                      "in XkorProgressiveThrowParadigm::scorinate(QList<XkorAthlete>)",
                      file=sys.stderr)
                self.out.append(("", "Sport does not support this paradigm"))
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
                    attempts = toList(r.result.get("attempts"))
                    attemptStrings = toList(r.result.get("attemptStrings"))
                    attempts.extend(toList(j.result.get("attempts")))
                    attemptStrings.extend(toList(j.result.get("attemptStrings")))
                    r.result["attempts"] = attempts
                    r.result["attemptStrings"] = attemptStrings

            priorAttempts = len(toList(r.result.get("attempts")))
            for j in range(priorAttempts, priorAttempts + toInt(self.opt.get("attempts", 1))):
                result = self.individualResult(i, "attempts")
                accuracyResult = self.individualResult(i, "accuracy", "accuracy")
                result.setScoreString(str(int(accuracyResult.score() * result.score()))
                                      + "/" + result.scoreString())
                result.setScore(int(accuracyResult.score() * result.score()))

                attempts = toList(r.result.get("attempts"))
                attemptStrings = toList(r.result.get("attemptStrings"))
                attempts.append(result.score())
                attemptStrings.append(result.scoreString())
                r.result["attempts"] = attempts
                r.result["attemptStrings"] = attemptStrings
                if (toString(self.opt.get("totalType")) != "best"
                        and (result.score() == sys.float_info.max
                             or result.score() == -sys.float_info.max)):
                    break
            self.calculateTotal(r)

            self.res.append(r)

        self.generateOutput()
