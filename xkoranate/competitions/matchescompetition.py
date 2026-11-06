from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition


class XkorMatchesCompetition(XkorAbstractCompetition):
    competitionType = "matches"

    def hasOptionsWidget(self):
        return True

    def matchdays(self):
        return 1

    def matchdayNames(self):
        return ["Mass start"]

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.matchescompetitionoptions import XkorMatchesCompetitionOptions

        return XkorMatchesCompetitionOptions(competitionOptions)

    def _pairings(self):
        """(group name, fixtures) for each group, its entrants paired off
        in order."""
        rval = []
        for g in self.startList.groups:
            size = len(g.athletes) - (len(g.athletes) % 2)
            rval.append((g.name, [(g.athletes[h], g.athletes[h + 1]) for h in range(0, size, 2)]))
        return rval

    def schedule(self):
        return "\n".join(self._fixtureLines(self._pairings(), self._formatFixture,
                                            len(self.startList.groups) > 1))

    def supportsOdds(self):
        return self._oddsParadigm() is not None

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        if p is None:
            return None

        return self._oddsText(self._fixtureLines(
            self._pairings(), lambda home, away: self._formatOdds(p, home, away, trials),
            len(self.startList.groups) > 1))

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
