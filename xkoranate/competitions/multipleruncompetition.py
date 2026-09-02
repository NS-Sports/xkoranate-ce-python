import sys

from ..uuids import parseUuid
from xkoranate.athlete import XkorAthlete
from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.result import XkorResult
from xkoranate.variant import toDouble, toInt, toList, toString

DBL_MAX = sys.float_info.max  # numeric_limits<double>::max()
DBL_MIN = sys.float_info.min  # numeric_limits<double>::min()


class XkorMultipleRunCompetition(XkorAbstractCompetition):
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
                truncatedScores = []
                truncatedScoreStrings = []
                for j in range(matchday):
                    truncatedScores.append(toList(currentScores[i])[j])
                    truncatedScoreStrings.append(toList(currentScoreStrings[i])[j])
                scores.append(truncatedScores)
                scoreStrings.append(truncatedScoreStrings)
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
                truncatedScores = []
                truncatedScoreStrings = []
                for j in range(matchday):
                    truncatedScores.append(toList(currentDQScores[i])[j])
                    truncatedScoreStrings.append(toList(currentDQScoreStrings[i])[j])
                scores.append(truncatedScores)
                scoreStrings.append(truncatedScoreStrings)
            else:
                disqualifiedAthletes.append(currentDQAthletes[i])
                disqualifiedScores.append(currentDQScores[i])
                disqualifiedScoreStrings.append(currentDQScoreStrings[i])
                disqualifiedOutputs.append(currentDQOutputs[i])

        self.resumeOpt["athletes"] = athletes
        self.resumeOpt["scores"] = scores
        self.resumeOpt["scoreStrings"] = scoreStrings
        self.resumeOpt["disqualifiedAthletes"] = disqualifiedAthletes
        self.resumeOpt["disqualifiedScores"] = disqualifiedScores
        self.resumeOpt["disqualifiedScoreStrings"] = disqualifiedScoreStrings
        self.resumeOpt["disqualifiedOutputs"] = disqualifiedOutputs
        return dict(self.resumeOpt)

    def scorinate(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["runNumber"] = matchday  # pass the run number to the paradigm for results formatting and such
        localParadigmOptions["nameWidth"] = self.nameWidth()

        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

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
                ath = XkorAthlete()
                for j in sl.athletes:
                    if parseUuid(toString(athletes[i])) == j.id:
                        ath = j.clone()

                r = XkorResult()
                r.athlete = ath
                attempts = []
                attemptStrings = []
                attempts.extend(toList(scores[i]))
                attemptStrings.extend(toList(scoreStrings[i]))
                r.result["attempts"] = attempts
                r.result["attemptStrings"] = attemptStrings

                athleteList.append(ath)
                previousResults.append(r)
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
            ath = XkorAthlete()
            for j in sl.athletes:
                if parseUuid(toString(disqualifiedAthletes[i])) == j.id:
                    ath = j.clone()

            r = XkorResult()
            r.athlete = ath
            attempts = []
            attemptStrings = []
            attempts.extend(toList(disqualifiedScores[i]))
            attemptStrings.extend(toList(disqualifiedScoreStrings[i]))
            r.result["attempts"] = attempts
            r.result["attemptStrings"] = attemptStrings
            r.setScore(toDouble(attempts[len(attempts) - 1]))
            r.setScoreString(toString(attemptStrings[len(attempts) - 1]))
            r.setOutput(toString(disqualifiedOutputs[i]))
            disqualifiedResults.append(r)

        p.addResults(disqualifiedResults)
        results = list(p.results())

        if toString(self.userOpt.get("sortResults", "true")) == "true":
            if toString(self.userOpt.get("sortByBestResult", "true")) == "true":
                p.comparisonFunction().sort(results)
            else:
                p.comparisonFunction("noTiebreakers").sort(results)

        # save the qualifiers
        qualifiedAthletes = []
        qualifyingScores = []
        qualifyingScoreStrings = []
        disqualifiedAthletes = []
        disqualifiedScores = []
        disqualifiedScoreStrings = []
        disqualifiedOutputs = []
        for i in range(len(results)):
            if results[i].score() != DBL_MAX and results[i].score() != DBL_MIN:
                qualifiedAthletes.append(toString(results[i].athlete.id))
                qualifyingScores.append(results[i].result.get("attempts"))
                qualifyingScoreStrings.append(results[i].result.get("attemptStrings"))
            else:
                disqualifiedAthletes.append(toString(results[i].athlete.id))
                disqualifiedScores.append(results[i].result.get("attempts"))
                disqualifiedScoreStrings.append(results[i].result.get("attemptStrings"))
                disqualifiedOutputs.append(results[i].output())
        self.resumeOpt["athletes"] = qualifiedAthletes
        self.resumeOpt["scores"] = qualifyingScores
        self.resumeOpt["scoreStrings"] = qualifyingScoreStrings
        self.resumeOpt["disqualifiedAthletes"] = disqualifiedAthletes
        self.resumeOpt["disqualifiedScores"] = disqualifiedScores
        self.resumeOpt["disqualifiedScoreStrings"] = disqualifiedScoreStrings
        self.resumeOpt["disqualifiedOutputs"] = disqualifiedOutputs

        if toString(self.userOpt.get("sortResults", "true")) == "true":
            if toString(self.userOpt.get("sortByBestResult", "true")) == "true":
                self.resultsBuf[matchday] = self.rankedListOutput(sl.name, results, p.comparisonFunction())
            else:
                self.resultsBuf[matchday] = self.rankedListOutput(sl.name, results, p.comparisonFunction("noTiebreakers"))
        else:
            self.resultsBuf[matchday] += sl.name + "\n"
            self.resultsBuf[matchday] += p.output() + "\n\n"
