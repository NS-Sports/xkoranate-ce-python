from xkoranate.competitions.conference import conferenceSchedule
from xkoranate.competitions.roundrobincompetition import (
    XkorRoundRobinCompetition, formatStoredMatch, parseStoredMatch)
from xkoranate.variant import toInt, toList, toString

OVERALL_TABLE_NAME = "Overall"


class XkorInterConferenceCompetition(XkorRoundRobinCompetition):
    """A league split into conferences, one per group.

    Teams play a round robin within their conference and also meet every
    team in every other conference. Each conference's table counts all of
    its teams' games, cross-conference ones included, and an overall table
    can rank everyone together.
    """

    # results are kept in one list rather than RR's list per group, so they
    # go under their own key: switching an event between the two types in
    # the editor can't feed one format to the other
    DATA_KEY = "conferenceTableData"

    def __init__(self, *args, **kwargs):
        self._scheduleCache = None
        super().__init__(*args, **kwargs)

    def init(self, sl, s, paradigmOptions, competitionOptions, results):
        super().init(sl, s, paradigmOptions, competitionOptions, results)
        self._scheduleCache = None
        # a conference table can't hold a grid against teams outside it
        self.userOpt["showResultsGrid"] = "false"

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.interconferencecompetitionoptions import \
            XkorInterConferenceCompetitionOptions

        return XkorInterConferenceCompetitionOptions(competitionOptions)

    # options

    def ownLegs(self):
        return toInt(self.userOpt.get("numberOfLegs")) if "numberOfLegs" in self.userOpt else 2

    def otherLegs(self):
        return toInt(self.userOpt.get("interConferenceLegs")) if "interConferenceLegs" in self.userOpt else 1

    def crossPoints(self):
        """(win, draw, loss) for games between conferences, or None when
        they score the same as games within one."""
        keys = ("crossPointsForWin", "crossPointsForDraw", "crossPointsForLoss")
        if not any(k in self.userOpt for k in keys):
            return None
        defaults = (toInt(self.userOpt.get("pointsForWin")) if "pointsForWin" in self.userOpt else 3,
                    toInt(self.userOpt.get("pointsForDraw")) if "pointsForDraw" in self.userOpt else 1,
                    toInt(self.userOpt.get("pointsForLoss")) if "pointsForLoss" in self.userOpt else 0)
        return tuple(toInt(self.userOpt.get(k)) if k in self.userOpt else d
                     for k, d in zip(keys, defaults))

    def showOverallTable(self):
        return toString(self.userOpt.get("showOverallTable")) != "false"

    # schedule

    def conferenceSchedule(self):
        key = (tuple(len(g.athletes) for g in self.startList.groups), self.ownLegs(), self.otherLegs())
        if self._scheduleCache is None or self._scheduleCache[0] != key:
            self._scheduleCache = (key, conferenceSchedule(key[0], key[1], key[2]))
        return self._scheduleCache[1]

    def matchdays(self):
        return len(self.conferenceSchedule())

    def _day(self, matchday):
        days = self.conferenceSchedule()
        return days[matchday] if 0 <= matchday < len(days) else []

    def _team(self, team):
        return self.startList.groups[team[0]].athletes[team[1]]

    def sectionName(self, section):
        """The group's own name, or “Pacific v Atlantic” for cross play."""
        return " v ".join(self.startList.groups[c].name for c in section.conferences)

    def schedule(self):
        days = self.conferenceSchedule()
        if not days:
            return None

        lines = []
        for name, day in zip(self.matchdayNames(), days):
            lines.append(name)
            for section in day:
                lines.append(self.sectionName(section))
                for home, away in section.fixtures:
                    lines.append(self._formatFixture(self._team(home), self._team(away)))
            lines.append("")
        return "\n".join(lines)

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        if p is None or not self.conferenceSchedule():
            return None

        lines = []
        for section in self._day(matchday):
            lines.append(self.sectionName(section))
            for home, away in section.fixtures:
                lines.append(self._formatOdds(p, self._team(home), self._team(away), trials))
        return "\n".join(lines) + ("\n" if lines else "")

    # results

    def _storedResults(self, before):
        """Saved result lines from matchdays before the given one."""
        rval = []
        for line in toList(self.userOpt.get(self.DATA_KEY)):
            parsed = parseStoredMatch(line)
            if parsed is not None and parsed[0] < before:
                rval.append(toString(line))
        return rval

    def _newTable(self, heading, teams, matches):
        from xkoranate.tablegenerator.table import XkorTable

        t = XkorTable()
        t.setColumns(self.generateTableColumns(heading, len(teams)))
        t.setSortCriteria(self.tableSortCriteria())
        self.setTablePoints(t)
        t.setConferences({a.name: n for n, g in enumerate(self.startList.groups) for a in g.athletes})
        t.setCrossPoints(self.crossPoints())
        t.setMatches(matches)
        t.setTeams(teams)
        # list every team from the start, even one yet to play
        for name in teams:
            t.findTeam(name)
        return t

    def scorinate(self, matchday):
        if not self._day(matchday):
            return

        stored = self._storedResults(matchday)
        matches = [parseStoredMatch(line)[1] for line in stored]

        self.tables = []
        for g in self.startList.groups:
            if g.athletes:
                self.tables.append(self._newTable(g.name, [a.name for a in g.athletes], matches))
        if self.showOverallTable() and len(self.tables) > 1:
            everyone = [a.name for g in self.startList.groups for a in g.athletes]
            self.tables.append(self._newTable(OVERALL_TABLE_NAME, everyone, matches))

        self.resumeOpt[self.DATA_KEY] = stored
        self.resultsBuf[matchday] = ""
        self.scorinateMatchday(matchday)
        self.resultsBuf[matchday] += "\n"

    def scorinateMatchday(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory
        from xkoranate.tablegenerator.tablematch import XkorTableMatch

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()
        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

        allowDraws = toString(self.userOpt.get("allowDraws")) != "false"
        stored = toList(self.resumeOpt.get(self.DATA_KEY))
        output = ""

        for section in self._day(matchday):
            athletes = []
            for home, away in section.fixtures:
                athletes.append(self._team(home))
                athletes.append(self._team(away))

            p.scorinate(athletes)

            if not allowDraws:
                # if there’s a tie, deal with it
                results = list(p.results())
                for j in range(0, len(results) - (len(results) % 2), 2):
                    if p.compare(results[j], results[j + 1]) == 0:
                        p.breakTie([results[j].athlete, results[j + 1].athlete])

            output += self.sectionName(section) + "\n" + p.output() + "\n"

            for home, away in section.fixtures:
                homeAthlete, awayAthlete = self._team(home), self._team(away)
                score1 = p.findResult(homeAthlete.id)
                score2 = p.findResult(awayAthlete.id)

                # with draws allowed a tie is a result in its own right,
                # so the tiebreaker stages don't come into the table
                if allowDraws:
                    value1, value2, decider = score1.score(), score2.score(), None
                else:
                    value1, value2, decider = self.effectiveScores(p, score1, score2)

                match = XkorTableMatch(homeAthlete.name, awayAthlete.name, value1, value2, decider)
                for t in self.tables:
                    t.insertMatch(match)
                stored.append(formatStoredMatch(matchday, homeAthlete.name, awayAthlete.name, value1, value2, decider))

        for t in self.tables:
            t.generate()
            output += t.toText() + "\n"

        self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + output
        self.resumeOpt[self.DATA_KEY] = stored

    def revertToMatchday(self, matchday):
        # “matchday” is the first that will be erased
        for k in list(self.resultsBuf.keys()):
            if k >= matchday:
                self.resultsBuf[k] = ""
        self.resumeOpt[self.DATA_KEY] = self._storedResults(matchday)
        return dict(self.resumeOpt)
