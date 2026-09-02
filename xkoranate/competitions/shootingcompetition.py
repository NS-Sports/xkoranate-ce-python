
from ..uuids import parseUuid
from xkoranate.athlete import XkorAthlete
from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.result import XkorResult
from xkoranate.variant import toDouble, toInt, toList, toString


class XkorShootingCompetition(XkorAbstractCompetition):
    def hasOptionsWidget(self):
        return True

    def matchdays(self):
        return 2

    def matchdayNames(self):
        return ["Qualifying", "Final"]

    def newOptionsWidget(self, options):
        from xkoranate.competitions.options.shootingcompetitionoptions import XkorShootingCompetitionOptions

        return XkorShootingCompetitionOptions(options)

    def scorinate(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()
        if matchday == 0:
            localParadigmOptions["qualifying"] = "true"

        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

        self.resultsBuf[matchday] = ""
        sl = self.startList.groups[0]

        # figure out who we’re scorinating
        athleteList = []
        previousResults = []
        if matchday == 1:
            qualifiers = toList(self.userOpt.get("qualifiers"))
            qualifyingScores = toList(self.userOpt.get("scores"))
            i = 0
            while i < len(qualifiers) and i < len(qualifyingScores):
                ath = XkorAthlete()
                for j in sl.athletes:
                    if parseUuid(toString(qualifiers[i])) == j.id:
                        ath = j.clone()
                previousResults.append(XkorResult(toDouble(qualifyingScores[i]), ath=ath))
                athleteList.append(ath)
                i += 1
        else:
            athleteList = list(sl.athletes)

        p.scorinate(athleteList, previousResults)

        results = list(p.results())

        # if there’s a tie, deal with it
        needsTiebreak = False
        while True:
            needsTiebreak = False
            results = list(p.results())
            p.comparisonFunction().sort(results)

            tiebreakAthletes = []
            tiebreakResults = []
            if matchday == 0:  # qualifying
                cutoff = toInt(self.userOpt.get("cutoff"))
                if cutoff > 0 and cutoff < len(results) and p.compare(results[cutoff - 1], results[cutoff]) == 0:
                    tiebreakResults.append(results[cutoff])
            else:  # final
                i = 1
                while i <= 3 and i < len(results):
                    if p.compare(results[i - 1], results[i]) == 0:
                        tiebreakResults.append(results[i])
                    i += 1

            if len(tiebreakResults) != 0:
                needsTiebreak = True
                for i in results:
                    for j in tiebreakResults:
                        if p.compare(i, j) == 0:
                            tiebreakAthletes.append(i.athlete)

            p.breakTie(tiebreakAthletes)

            if not needsTiebreak:
                break

        # save the qualifiers
        if matchday == 0:
            cutoff = len(results) if toInt(self.userOpt.get("cutoff")) == 0 else toInt(self.userOpt.get("cutoff"))
            qualifiedAthletes = []
            qualifyingScores = []
            for i in range(cutoff):
                qualifiedAthletes.append(toString(results[i].athlete.id))
                qualifyingScores.append(results[i].score())
            self.resumeOpt["qualifiers"] = qualifiedAthletes
            self.resumeOpt["scores"] = qualifyingScores

        self.resultsBuf[matchday] = self.rankedListOutput(sl.name, results, p.comparisonFunction())
