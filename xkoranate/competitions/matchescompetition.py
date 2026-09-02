from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.variant import toString


class XkorMatchesCompetition(XkorAbstractCompetition):
    def hasOptionsWidget(self):
        return True

    def matchdays(self):
        return 1

    def matchdayNames(self):
        return ["Mass start"]

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.matchescompetitionoptions import XkorMatchesCompetitionOptions

        return XkorMatchesCompetitionOptions(competitionOptions)

    def schedule(self):
        lines = []
        for i in self.startList.groups:
            size = len(i.athletes) - (len(i.athletes) % 2)
            if size == 0:
                continue
            if len(self.startList.groups) > 1:
                lines.append(i.name)
            for home in range(0, size, 2):
                lines.append(self._formatFixture(i.athletes[home], i.athletes[home + 1]))
        return "\n".join(lines)

    def supportsOdds(self):
        return self._oddsParadigm() is not None

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        if p is None:
            return None

        lines = []
        for i in self.startList.groups:
            size = len(i.athletes) - (len(i.athletes) % 2)
            if size == 0:
                continue
            if len(self.startList.groups) > 1:
                lines.append(i.name)
            for home in range(0, size, 2):
                lines.append(self._formatOdds(p, i.athletes[home], i.athletes[home + 1], trials))
        return "\n".join(lines) + ("\n" if lines else "")

    def scorinate(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()

        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

        self.resultsBuf[matchday] = ""
        for i in self.startList.groups:
            self.resultsBuf[matchday] += i.name + "\n"
            p.scorinate(list(i.athletes))

            if toString(self.userOpt.get("allowDraws")) == "false":
                # if there’s a tie, deal with it
                results = list(p.results())
                for j in range(0, len(i.athletes) - (len(i.athletes) % 2), 2):
                    score1 = results[j]
                    score2 = results[j + 1]
                    if p.compare(score1, score2) == 0:
                        tiebreakAthletes = [score1.athlete, score2.athlete]
                        p.breakTie(tiebreakAthletes)

            self.resultsBuf[matchday] += p.output()
            self.resultsBuf[matchday] += "\n"
