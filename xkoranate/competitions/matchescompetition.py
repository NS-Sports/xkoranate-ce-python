from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition


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
        p = self._newParadigm()

        self.resultsBuf[matchday] = ""
        for i in self.startList.groups:
            self.resultsBuf[matchday] += i.name + "\n"
            p.scorinate(list(i.athletes))

            if not self.allowsDraws():
                # if there’s a tie, deal with it
                self._breakDrawnPairs(p, len(i.athletes))

            self.resultsBuf[matchday] += p.output()
            self.resultsBuf[matchday] += "\n"
