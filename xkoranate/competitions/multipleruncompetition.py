import sys

from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.result import XkorResult
from xkoranate.variant import toDouble, toInt, toList, toString

DBL_MAX = sys.float_info.max  # numeric_limits<double>::max()

# the resume options carrying the runs so far: the athletes still in, their
# scores and score strings, then the same for the disqualified, plus their
# output lines
RUN_KEYS = ("athletes", "scores", "scoreStrings", "disqualifiedAthletes", "disqualifiedScores",
            "disqualifiedScoreStrings", "disqualifiedOutputs")


class XkorMultipleRunCompetition(XkorAbstractCompetition):
    competitionType = "multipleRun"

    def hasOptionsWidget(self):
        return True

    def matchdays(self):
        return toInt(self.userOpt.get("runs", 2))

    def matchdayNames(self):
        rval = []
        for i in range(1, toInt(self.userOpt.get("runs", 2)) + 1):
            rval.append("Run %d" % i)
        return rval

    def newOptionsWidget(self, options):
        from xkoranate.competitions.options.multipleruncompetitionoptions import XkorMultipleRunCompetitionOptions

        return XkorMultipleRunCompetitionOptions(options)

    def _saveRuns(self, *values):
        """Store the RUN_KEYS resume options, in that order."""
        for key, value in zip(RUN_KEYS, values):
            self.resumeOpt[key] = value

    @staticmethod
    def _firstRuns(values, i, runs):
        """The first `runs` entries of values[i]."""
        return [toList(values[i])[j] for j in range(runs)]

    @staticmethod
    def _resultFromAttempts(athlete, attempts, attemptStrings):
        r = XkorResult()
        r.athlete = athlete
        r.result["attempts"] = list(toList(attempts))
        r.result["attemptStrings"] = list(toList(attemptStrings))
        return r

    def _comparator(self, p):
        """The comparator results are ranked by, or None if they stay
        unsorted."""
        if toString(self.userOpt.get("sortResults", "true")) != "true":
            return None
        if toString(self.userOpt.get("sortByBestResult", "true")) == "true":
            return p.comparisonFunction()
        return p.comparisonFunction("noTiebreakers")

    def revertToMatchday(self, matchday):
        athletes = []
        scores = []
        scoreStrings = []
        disqualifiedAthletes = []
        disqualifiedScores = []
        disqualifiedScoreStrings = []
        disqualifiedOutputs = []

        currentAthletes = toList(self.userOpt.get("athletes"))
        currentScores = toList(self.userOpt.get("scores"))
        currentScoreStrings = toList(self.userOpt.get("scoreStrings"))
        for i in range(len(currentAthletes)):
            athletes.append(currentAthletes[i])
            if len(toList(currentScores[i])) >= matchday:
                scores.append(self._firstRuns(currentScores, i, matchday))
                scoreStrings.append(self._firstRuns(currentScoreStrings, i, matchday))
            else:
                scores.append(currentScores[i])
                scoreStrings.append(currentScoreStrings[i])

        currentDQAthletes = toList(self.userOpt.get("disqualifiedAthletes"))
        currentDQScores = toList(self.userOpt.get("disqualifiedScores"))
        currentDQScoreStrings = toList(self.userOpt.get("disqualifiedScoreStrings"))
        currentDQOutputs = toList(self.userOpt.get("disqualifiedOutputs"))
        for i in range(len(currentDQAthletes)):
            if len(toList(currentDQScores[i])) > matchday:
                # return them to active duty
                athletes.append(currentDQAthletes[i])
                scores.append(self._firstRuns(currentDQScores, i, matchday))
                scoreStrings.append(self._firstRuns(currentDQScoreStrings, i, matchday))
            else:
                disqualifiedAthletes.append(currentDQAthletes[i])
                disqualifiedScores.append(currentDQScores[i])
                disqualifiedScoreStrings.append(currentDQScoreStrings[i])
                disqualifiedOutputs.append(currentDQOutputs[i])

        self._saveRuns(athletes, scores, scoreStrings, disqualifiedAthletes, disqualifiedScores,
                       disqualifiedScoreStrings, disqualifiedOutputs)
        return dict(self.resumeOpt)

    def scorinate(self, matchday):
        # pass the run number to the paradigm for results formatting and such
        p = self._newParadigm(runNumber=matchday)

        self.resultsBuf[matchday] = ""
        sl = self.startList.groups[0]

        # figure out who we’re scorinating
        athleteList = []
        previousResults = []
        if matchday > 0:
            athletes = toList(self.userOpt.get("athletes"))
            scores = toList(self.userOpt.get("scores"))
            scoreStrings = toList(self.userOpt.get("scoreStrings"))
            for i in range(len(athletes)):
                ath = self._savedAthlete(sl.athletes, athletes[i])
                athleteList.append(ath)
                previousResults.append(self._resultFromAttempts(ath, scores[i], scoreStrings[i]))
        else:
            athleteList = list(sl.athletes)

        p.scorinate(athleteList, previousResults)

        # insert disqualified athletes
        disqualifiedResults = []
        disqualifiedAthletes = toList(self.userOpt.get("disqualifiedAthletes"))
        disqualifiedScores = toList(self.userOpt.get("disqualifiedScores"))
        disqualifiedScoreStrings = toList(self.userOpt.get("disqualifiedScoreStrings"))
        disqualifiedOutputs = toList(self.userOpt.get("disqualifiedOutputs"))
        for i in range(len(disqualifiedAthletes)):
            r = self._resultFromAttempts(self._savedAthlete(sl.athletes, disqualifiedAthletes[i]),
                                         disqualifiedScores[i], disqualifiedScoreStrings[i])
            attempts, attemptStrings = r.result["attempts"], r.result["attemptStrings"]
            r.setScore(toDouble(attempts[len(attempts) - 1]))
            r.setScoreString(toString(attemptStrings[len(attempts) - 1]))
            r.setOutput(toString(disqualifiedOutputs[i]))
            disqualifiedResults.append(r)

        p.addResults(disqualifiedResults)
        results = list(p.results())

        comparator = self._comparator(p)
        if comparator is not None:
            comparator.sort(results)

        # save the qualifiers
        qualifiedAthletes = []
        qualifyingScores = []
        qualifyingScoreStrings = []
        disqualifiedAthletes = []
        disqualifiedScores = []
        disqualifiedScoreStrings = []
        disqualifiedOutputs = []
        for i in range(len(results)):
            # a failure scores DBL_MAX, or -DBL_MAX in a descending sport; the
            # C++ tested numeric_limits<double>::min(), the smallest positive
            # double, so a failure in a descending sport went on to the next run
            if results[i].score() != DBL_MAX and results[i].score() != -DBL_MAX:
                qualifiedAthletes.append(toString(results[i].athlete.id))
                qualifyingScores.append(results[i].result.get("attempts"))
                qualifyingScoreStrings.append(results[i].result.get("attemptStrings"))
            else:
                disqualifiedAthletes.append(toString(results[i].athlete.id))
                disqualifiedScores.append(results[i].result.get("attempts"))
                disqualifiedScoreStrings.append(results[i].result.get("attemptStrings"))
                disqualifiedOutputs.append(results[i].output())
        self._saveRuns(qualifiedAthletes, qualifyingScores, qualifyingScoreStrings, disqualifiedAthletes,
                       disqualifiedScores, disqualifiedScoreStrings, disqualifiedOutputs)

        if comparator is not None:
            self.resultsBuf[matchday] = self.rankedListOutput(sl.name, results, comparator)
        else:
            self.resultsBuf[matchday] += sl.name + "\n"
            self.resultsBuf[matchday] += p.output() + "\n\n"
