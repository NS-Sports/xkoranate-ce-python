import sys

from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .timedparadigm import XkorTimedParadigm


class XkorPGSParadigm(XkorTimedParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions = {}
        self.supportedCompetitions["matches"] = True

    def newOptionsWidget(self, paradigmOptions):
        from .options.pgsparadigmoptions import XkorPGSParadigmOptions
        return XkorPGSParadigmOptions(paradigmOptions)

    def calculateTotal(self, r):
        attempts = toList(r.result.get("attempts"))
        attemptStrings = toList(r.result.get("attemptStrings"))
        r.setScore(toDouble(attempts[len(attempts) - 1]))
        r.setScoreString(toString(attemptStrings[len(attemptStrings) - 1]))

        r.setOutput(self.outputLine(r))

    def formatScore(self, score):
        return "+" + XkorTimedParadigm.formatScore(self, score)

    def outputLine(self, r):
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 5)) + 2

        rval = self.formatName(r.athlete.name, r.athlete.nation).ljust(nameWidth)
        attemptStrings = toList(r.value("attemptStrings"))
        for i in attemptStrings:
            rval += toString(i).rjust(resultWidth)

        return rval

    def scorinate(self, athletes, previousResults=None):
        # initialize results
        self.out = []
        self.res = []

        for home, away in self._pairs(athletes):
            homeResult = XkorResult()
            awayResult = XkorResult()
            homeResult.athlete = home.clone()
            awayResult.athlete = away.clone()

            for i in range(toInt(self.opt.get("attempts", 1))):
                # scorinate the home result
                result = self.individualResult(home, "score")
                self._appendAttempt(homeResult, result.score(), result.scoreString())

                # scorinate the away result
                result = self.individualResult(away, "score")
                self._appendAttempt(awayResult, result.score(), result.scoreString())

            # sort out PGS stuff
            totalHomeScore = 0.0
            totalAwayScore = 0.0
            thisScore = 0.0
            maxScore = toDouble(self.userOpt.get("maxScore", 1.5))
            for i in range(toInt(self.opt.get("attempts", 1))):
                if toList(homeResult.value("attempts"))[i] == sys.float_info.max:
                    totalHomeScore = maxScore
                    totalAwayScore = 0
                    self._setAttempt(awayResult, i, 0, "")
                elif toList(awayResult.value("attempts"))[i] == sys.float_info.max:
                    totalAwayScore = maxScore
                    totalHomeScore = 0
                    self._setAttempt(homeResult, i, 0, "")
                else:
                    totalHomeScore += toDouble(toList(homeResult.value("attempts"))[i])
                    totalAwayScore += toDouble(toList(awayResult.value("attempts"))[i])
                    if totalHomeScore > totalAwayScore:
                        totalHomeScore -= totalAwayScore
                        thisScore = totalHomeScore
                        if totalHomeScore > maxScore:
                            totalHomeScore = maxScore
                        totalAwayScore = 0

                        self._setAttempt(homeResult, i, thisScore, self.formatScore(thisScore))
                        self._setAttempt(awayResult, i, 0, "")
                    else:
                        totalAwayScore -= totalHomeScore
                        thisScore = totalAwayScore
                        if totalAwayScore > maxScore:
                            totalAwayScore = maxScore
                        totalHomeScore = 0

                        self._setAttempt(homeResult, i, 0, "")
                        self._setAttempt(awayResult, i, thisScore, self.formatScore(thisScore))
                print(totalHomeScore, totalAwayScore, file=sys.stderr)

            homeResult.setOutput(self.outputLine(homeResult))
            awayResult.setOutput(self.outputLine(awayResult) + "\n")

            self.res.append(homeResult)
            self.res.append(awayResult)

        self.generateOutput()
