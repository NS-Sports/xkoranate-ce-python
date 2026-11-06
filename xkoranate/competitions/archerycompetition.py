from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.result import XkorResult
from xkoranate.variant import toInt


class XkorArcheryCompetition(XkorAbstractCompetition):
    competitionType = "archery"

    def hasOptionsWidget(self):
        return True

    def matchdays(self):
        return 1

    def matchdayNames(self):
        return ["Ranking round"]

    def newOptionsWidget(self, options):
        from xkoranate.competitions.options.archerycompetitionoptions import XkorArcheryCompetitionOptions

        return XkorArcheryCompetitionOptions(options)

    def scorinate(self, matchday):
        p = self._newParadigm(rankingRound="true")

        self.resultsBuf[matchday] = ""
        sl = self.startList.groups[0]
        p.scorinate(list(sl.athletes))

        # if there’s a tie, deal with it
        results = list(p.results())
        needsTiebreak = False
        i = 0
        while True:
            needsTiebreak = False
            results = list(p.results())
            p.comparisonFunction().sort(results)
            lotsTiebreakAthletes = []
            realTiebreakAthletes = []
            tieResult = XkorResult()

            position = 0
            for idx in range(len(results) - 1):
                prev = results[idx]  # make prev be what i was
                cur = results[idx + 1]
                if p.compare(prev, cur) == 0:
                    if position == toInt(self.userOpt.get("cutoff")) - 1:
                        tieResult = cur
                    elif prev.athlete in lotsTiebreakAthletes:
                        lotsTiebreakAthletes.append(cur.athlete)
                    else:
                        lotsTiebreakAthletes.append(prev.athlete)
                        lotsTiebreakAthletes.append(cur.athlete)
                    needsTiebreak = True
                position += 1

            for j in results:
                if p.compare(tieResult, j) == 0:
                    realTiebreakAthletes.append(j.athlete)
                    if j.athlete in lotsTiebreakAthletes:
                        del lotsTiebreakAthletes[lotsTiebreakAthletes.index(j.athlete)]

            p.breakTie(lotsTiebreakAthletes, "lots")
            if i < 3:
                p.breakTie(realTiebreakAthletes)
            else:
                p.breakTie(realTiebreakAthletes, "closest")  # closest arrow to the center
            i += 1

            if not needsTiebreak:
                break

        self.resultsBuf[matchday] = self.rankedListOutput(sl.name, results, p.comparisonFunction())
