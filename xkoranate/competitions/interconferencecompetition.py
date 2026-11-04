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

    def _sections(self, day):
        """(section name, fixtures) for each section of a matchday."""
        return [(self.sectionName(s), [(self._team(h), self._team(a)) for h, a in s.fixtures])
                for s in day]

    def schedule(self):
        days = self.conferenceSchedule()
        if not days:
            return None

        lines = []
        for name, day in zip(self.matchdayNames(), days):
            lines.append(name)
            lines += self._fixtureLines(self._sections(day), self._formatFixture)
            lines.append("")
        return "\n".join(lines)

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        if p is None or not self.conferenceSchedule():
            return None

        return self._oddsText(self._fixtureLines(
            self._sections(self._day(matchday)),
            lambda home, away: self._formatOdds(p, home, away, trials)))

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
        from xkoranate.tablegenerator.tablematch import XkorTableMatch

        p = self._newParadigm()
        allowDraws = self.allowsDraws()
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
                self._breakDrawnPairs(p)

            output += self.sectionName(section) + "\n" + p.output() + "\n"

            for home, away in section.fixtures:
                homeAthlete, awayAthlete = self._team(home), self._team(away)
                score1 = p.findResult(homeAthlete.id)
                score2 = p.findResult(awayAthlete.id)

                value1, value2, decider = self.tableScores(p, score1, score2, allowDraws)

                match = XkorTableMatch(homeAthlete.name, awayAthlete.name, value1, value2, decider)
                for t in self.tables:
                    t.insertMatch(match)
                stored.append(formatStoredMatch(matchday, homeAthlete.name, awayAthlete.name, value1, value2, decider))

        for t in self.tables:
            t.generate()
            output += t.toText() + "\n"

        self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + output
        self.resumeOpt[self.DATA_KEY] = stored

    # qualification markers: conferences are the groups

    def _configureTable(self, t, sortCriteria):
        super()._configureTable(t, sortCriteria)
        t.setCrossPoints(self.crossPoints())

    def formatQualifications(self, text, matchday, settings):
        from xkoranate.competitions.qualification import leagueMarkers

        if not text or not settings.isEnabled() or not self._day(matchday):
            return text
        key = (text, matchday, settings)
        if key in self._qualificationCache:
            return self._qualificationCache[key]

        # rebuilt as scorinate() built them: every conference's table from
        # all the results so far, cross-conference ones included
        matches = [parseStoredMatch(line)[1] for line in self._storedResults(matchday + 1)]
        conferences = [g for g in self.startList.groups if g.athletes]
        tables = [self._rebuilt(text, self._newTable(g.name, [a.name for a in g.athletes], matches))
                  for g in conferences]

        markers = leagueMarkers(
            [self._conferenceGroup(g, t, matchday) for g, t in zip(conferences, tables)],
            settings, crossRank=lambda candidates: self._rankNextPlaced(candidates, tables))

        marked = list(zip(tables, markers))
        if self.showOverallTable() and len(tables) > 1:
            # the overall table repeats each team's mark from its conference
            everyone = [a.name for g in self.startList.groups for a in g.athletes]
            overall = self._rebuilt(text, self._newTable(OVERALL_TABLE_NAME, everyone, matches))
            marked.append((overall, {name: m for ms in markers for name, m in ms.items()}))

        rval = self._markTables(text, marked)
        self._qualificationCache[key] = rval
        return rval

    def _conferenceGroup(self, conference, table, matchday):
        from xkoranate.competitions.qualification import QualificationGroup

        names = [a.name for a in conference.athletes]
        inConference = set(names)
        remaining, games = [], dict.fromkeys(names, 0)
        for md, day in enumerate(self.conferenceSchedule()):
            for section in day:
                for home, away in section.fixtures:
                    h, a = self._team(home).name, self._team(away).name
                    if h not in inConference and a not in inConference:
                        continue
                    for team in (h, a):
                        if team in games:
                            games[team] += 1
                    if md > matchday:
                        # played against another conference: that game's
                        # points, and only this conference's side counts
                        remaining.append((h, a, home[0] != away[0]))

        # a win percentage compares across conferences only if every team
        # in this one plays the same number of games
        perTeam = set(games.values())
        metric, outcomes, scale = self._qualificationMetric(
            table, perTeam.pop() if len(perTeam) == 1 else None)
        if outcomes is not None:
            remaining = [(h, a, outcomes(cross)) for h, a, cross in remaining]
        else:
            remaining = [(h, a) for h, a, _cross in remaining]
        return QualificationGroup(
            teams=names, current=self._currentMetric(table, metric), remaining=remaining,
            outcomes=None if outcomes is None else outcomes(False),
            order=[[r.name() for r in b] for b in table.data if b], scale=scale)

    def revertToMatchday(self, matchday):
        # “matchday” is the first that will be erased
        self._clearResultsFrom(matchday)
        self.resumeOpt[self.DATA_KEY] = self._storedResults(matchday)
        return dict(self.resumeOpt)
