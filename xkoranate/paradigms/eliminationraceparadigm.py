import sys

from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .comparators.eliminationraceresultcomparator import XkorEliminationRaceResultComparator
from .timedparadigm import XkorTimedParadigm


class XkorEliminationRaceParadigm(XkorTimedParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions = {}
        self.supportedCompetitions["standard"] = True

    # protected:

    def awardPoints(self, activeRes, lap, isFinal=False):
        bestResult = None
        secondBestResult = None
        thirdBestResult = None
        for j in activeRes:
            if bestResult is None or self.lapTime(j, lap) < self.lapTime(bestResult, lap):
                if bestResult is not None:
                    if secondBestResult is not None:
                        thirdBestResult = secondBestResult
                    secondBestResult = bestResult
                bestResult = j
            elif secondBestResult is None or self.lapTime(j, lap) < self.lapTime(secondBestResult, lap):
                if secondBestResult is not None:
                    thirdBestResult = secondBestResult
                secondBestResult = j
            elif thirdBestResult is None or self.lapTime(j, lap) < self.lapTime(thirdBestResult, lap):
                thirdBestResult = j
        if bestResult is not None:
            bestResult.result["points"] = toInt(bestResult.value("points")) + (3 if isFinal else 2)
        if secondBestResult is not None:
            secondBestResult.result["points"] = toInt(secondBestResult.value("points")) + (2 if isFinal else 1)
        if thirdBestResult is not None and isFinal:
            thirdBestResult.result["points"] = toInt(thirdBestResult.value("points")) + 1

    def comparisonFunction(self, type=""):
        return XkorEliminationRaceResultComparator(type, self.opt)

    def lapTime(self, r, lap):
        rval = 0.0
        attempts = toList(r.result.get("attempts"))
        i = 0
        while i < lap and i < len(attempts):
            rval += toDouble(attempts[i])
            i += 1
        return rval

    def outputLine(self, r):
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 9)) + 2
        usePoints = (toString(self.opt.get("usePoints")) == "true")

        rval = self.formatName(r.athlete.name, r.athlete.nation).ljust(nameWidth)
        rval += r.scoreString().rjust(resultWidth)
        if usePoints and r.score() != sys.float_info.max:
            rval += toString(r.value("points")).rjust(7)

        return rval

    def scorinate(self, athletes, previousResults=None):
        laps = toInt(self.opt.get("laps"))
        eliminations = len(athletes) - toInt(self.opt.get("finishers", 5))
        firstElimination = toInt(self.opt.get("firstElimination", 12))
        lastElimination = toInt(self.opt.get("lastElimination", 72))
        eliminationSlots = (lastElimination - firstElimination) // 2 + 1
        # C++ integer division truncates toward zero
        eliminationsPerSlot = int(eliminations / eliminationSlots)
        extraEliminations = eliminations - eliminationSlots * eliminationsPerSlot
        usePoints = (toString(self.opt.get("usePoints")) == "true")

        # initialize results
        self.out = []
        self.res = []

        activeRes = []
        for i in athletes:
            r = XkorResult()
            r.athlete = i.clone()

            for j in range(laps):
                result = self.individualResult(i, "score")
                self._appendAttempt(r, result.score(), result.scoreString())
            self.calculateTotal(r)

            activeRes.append(r)

        # award points for any sprints that don’t have corresponding eliminations
        if usePoints:
            for i in range(eliminationSlots - eliminations):
                self.awardPoints(activeRes, firstElimination + i * 2)

        lastPointsSprint = 0
        for i in range(eliminations):
            if eliminationsPerSlot > 0:
                extraEliminationsPassed = min(extraEliminations,
                                              (i + 1) // (eliminationsPerSlot + 1))  # integer division
                eliminationLap = (lastElimination
                                  - (eliminationSlots
                                     - (i - extraEliminationsPassed) // eliminationsPerSlot - 1) * 2)
            else:
                eliminationLap = lastElimination - (eliminations - i - 1) * 2

            # calculate points for previous lap if this is a points race
            if usePoints and lastPointsSprint < eliminationLap - 1:
                self.awardPoints(activeRes, eliminationLap - 1)
            lastPointsSprint = eliminationLap - 1

            worstResult = None
            for j in activeRes:
                if worstResult is None or self.lapTime(j, eliminationLap) > self.lapTime(worstResult, eliminationLap):
                    worstResult = j
            eliminated = worstResult.clone()
            eliminated.result["eliminationOrder"] = i + 1
            eliminated.setScore(sys.float_info.max)
            eliminated.setScoreString(f"EL lap {eliminationLap}")
            eliminated.setOutput(self.outputLine(eliminated))
            self.res.append(eliminated)
            activeRes.remove(eliminated)  # QList::removeOne — matches by athlete id

        # points for final finishing position
        if usePoints:
            self.awardPoints(activeRes, laps, True)

        # insert the actual finishers
        for i in activeRes:
            i.setOutput(self.outputLine(i))
            self.res.append(i)
