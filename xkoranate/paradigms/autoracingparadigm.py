import math
import sys

from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .abstractparadigm import XkorAbstractParadigm
from .timedparadigm import XkorTimedParadigm


class XkorAutoRacingParadigm(XkorTimedParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions = {}
        self.supportedCompetitions["standard"] = True

    def newAthleteWidget(self):
        if toString(self.userOpt.get("skillType")) == "attributes":
            from ..signuplisteditor.athletewidget import XkorAthleteWidget
            return XkorAthleteWidget(
                ["name", "nation", "acceleration", "cornering", "reliability"],
                ["Participant", "Team", "Acceleration", "Cornering", "Reliability"],
                ["string", "string", "double", "double", "double"],
                0, 10, 1)
        else:
            return super().newAthleteWidget()

    def newOptionsWidget(self, paradigmOptions):
        from .options.autoracingparadigmoptions import XkorAutoRacingParadigmOptions
        return XkorAutoRacingParadigmOptions(paradigmOptions)

    # protected:

    def individualResult(self, ath, lap=0):
        randCoeff = toDouble(self.opt.get("randCoeff", 0.6))
        randOffset = toDouble(self.opt.get("randBase", 0.6))
        skillCoeff = toDouble(self.opt.get("skillCoeff", 0.3))
        reliabilityCoeff = toDouble(self.opt.get("reliabilityCoeff", 0.03))

        lapRecord = toDouble(self.userOpt.get("lapRecord", 90))
        lapVariance = toDouble(self.userOpt.get("lapVariance", 15))
        trackAcceleration = toDouble(self.userOpt.get("trackAcceleration", 5))
        trackCornering = toDouble(self.userOpt.get("trackCornering", 5))
        useAttributes = toString(self.userOpt.get("skillType")) == "attributes"

        reliability = (toDouble(ath.property("reliability")) if useAttributes
                       else ath.skill * 10)
        if self.s.randUniform() < reliabilityCoeff / (1 + reliability):
            return XkorResult(sys.float_info.max,
                              toString(self.opt.get("unreliableText", "DNF")) + f" lap {lap}",
                              ath)

        if useAttributes:
            acceleration = toDouble(ath.property("acceleration"))
            cornering = toDouble(ath.property("cornering"))
            lapTime = lapRecord + lapVariance * math.pow(
                self.s.randUniform() * randCoeff + randOffset,
                skillCoeff * (acceleration * trackAcceleration + cornering * trackCornering)
                / (trackAcceleration + trackCornering))
        else:
            lapTime = lapRecord + lapVariance * math.pow(
                self.s.randUniform() * randCoeff + randOffset,
                skillCoeff * (ath.skill * 9 + 1))

        lapTime = self.roundScore(lapTime)
        return XkorResult(lapTime, self.formatScore(lapTime), ath)

    def outputLine(self, r):
        # exists purely to suppress XkorTimedParadigm's attempt-column output
        # and fall back to the plain base line — deliberately not super()
        return XkorAbstractParadigm.outputLine(self, r)

    def scorinate(self, athletes, previousResults=None):
        # initialize results
        self.out = []
        self.res = []

        laps = toInt(self.userOpt.get("laps", 50))
        isQualifying = toString(self.opt.get("totalType")) == "best"
        startingGridMultiplier = (toDouble(self.opt.get("startingGridPenalty", 2))
                                  if toString(self.userOpt.get("useStartingGrid")) == "true"
                                  else 0)

        startingGridPenalty = startingGridMultiplier
        for i in athletes:
            r = XkorResult()
            r.athlete = i.clone()

            for j in range(laps):
                result = self.individualResult(i, j + 1)

                attempts = toList(r.result.get("attempts"))
                attemptStrings = toList(r.result.get("attemptStrings"))
                attempts.append(result.score() + (startingGridPenalty if j == 0 else 0))
                if j == 0:
                    print(startingGridPenalty, file=sys.stderr)
                attemptStrings.append(result.scoreString())
                r.result["attempts"] = attempts
                r.result["attemptStrings"] = attemptStrings

                if not isQualifying and result.score() == sys.float_info.max:
                    break  # did not finish

            self.calculateTotal(r)

            self.res.append(r)
            startingGridPenalty += startingGridMultiplier

        # who’s on first?
        firstPlaceTime = sys.float_info.max
        for i in self.res:
            if i.score() < firstPlaceTime:
                firstPlaceTime = i.score()

        # calculate laps behind
        for i in self.res:
            attempts = toList(i.result.get("attempts"))
            currentTime = i.score()
            if currentTime != sys.float_info.max and currentTime > firstPlaceTime:
                j = 0
                while len(attempts) > 0:
                    # set the score according to finish on the current lap
                    i.setScore(currentTime + firstPlaceTime * j)
                    currentTime -= toDouble(attempts.pop())
                    if currentTime < firstPlaceTime:
                        # if j == 0, do nothing
                        if j == 1:
                            i.setScoreString("−1 lap")
                        elif j > 1:
                            i.setScoreString(f"−{j} laps")
                        i.setOutput(self.outputLine(i))
                        break
                    j += 1

        self.generateOutput()
