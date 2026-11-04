
import sys

from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.result import XkorResult
from xkoranate.variant import toDouble, toInt, toList, toString

# real shoot-offs settle within a handful of shots
MAX_SHOOTOFFS = 50


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
        p = self._newParadigm(qualifying="true") if matchday == 0 else self._newParadigm()

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
                ath = self._savedAthlete(sl.athletes, qualifiers[i])
                previousResults.append(XkorResult(toDouble(qualifyingScores[i]), ath=ath))
                athleteList.append(ath)
                i += 1
        else:
            athleteList = list(sl.athletes)

        p.scorinate(athleteList, previousResults)

        results = list(p.results())

        # if there’s a tie, deal with it. A shoot-off can only separate
        # athletes if the sport says how shoot-off shots score: without that
        # data every shot comes out the same and this loop never ended. Then
        # the tie stands, as it does after MAX_SHOOTOFFS rounds of shots that
        # still can't separate them.
        canShootOff = self.sport.hasValue("shootoffScore")
        shootoffs = 0
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

            if needsTiebreak and (not canShootOff or shootoffs >= MAX_SHOOTOFFS):
                print("can't break a tie by shoot-off in", self.sport.name(), file=sys.stderr)
                break

            p.breakTie(tiebreakAthletes)
            shootoffs += 1

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
