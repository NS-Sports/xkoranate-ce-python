import math
import re

from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.variant import qNumber, toDouble, toInt, toList, toString, toUInt


class XkorRoundRobinCompetition(XkorAbstractCompetition):
    def __init__(self, *args, **kwargs):
        self._qualificationCache = {}
        super().__init__(*args, **kwargs)
        self.tables = []  # QList<XkorTable>

    def hasOptionsWidget(self):
        return True

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.roundrobincompetitionoptions import XkorRoundRobinCompetitionOptions

        return XkorRoundRobinCompetitionOptions(competitionOptions)

    def scorinate(self, matchday):
        if self.largestGroupSize(self.startList) > 0:  # if there are no teams, don’t bother!
            # initialize the tables
            self.tables = []
            groupNo = 0
            for i in self.startList.groups:
                self.tables.append(self._newTable(i.name, self.retrieveMatches(groupNo)))
                groupNo += 1

            # initialize the results in the resume file options
            self.resumeOpt["tableData"] = self.userOpt.get("tableData")

            numberOfLegs = 1
            if "numberOfLegs" in self.userOpt:
                numberOfLegs = toUInt(self.userOpt.get("numberOfLegs"))  # noqa: F841 (unused in the C++ too)

            self.scorinateMatchday(matchday)
            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + "\n"

    def generateFixtures(self, matchday, groupSize):
        # account for possibility of more than two legs
        reverseFixtures = (matchday % (2 * (groupSize - 1)) >= groupSize - 1)  # if we’re in the 2nd, 4th, … leg, reverse home/away
        matchday %= (groupSize - 1)

        matchesPerRound = groupSize // 2
        fixtures = []

        # mix up the fixtures a bit
        round_ = matchday // 2
        if matchday & 1:
            round_ += groupSize // 2

        for m in range(matchesPerRound):
            home = (round_ + m) % (groupSize - 1)
            away = (groupSize - 1 - m + round_) % (groupSize - 1)
            if m == 0:
                away = groupSize - 1

            # flip the fixtures if:
            # if this is the first match of an odd matchday, flip so that the last team isn’t always away
            # if we’re on an even-numbered leg (reverseFixtures is set)
            # if both of these are true, “flip it twice,” i.e., don’t flip it (thus use of xor)
            if (m == 0 and (matchday & 1) != 0) != reverseFixtures:
                fixtures.append((away, home))
            else:
                fixtures.append((home, away))

        return fixtures

    def schedule(self):
        groupSize = self.largestGroupSize(self.startList)
        if groupSize == 0:
            return None

        matchdayNames = self.matchdayNames()
        lines = []
        for matchday in range(self.matchdays()):
            fixtures = self.generateFixtures(matchday, groupSize)
            lines.append(matchdayNames[matchday])
            for i in self.startList.groups:
                size = len(i.athletes)
                pairs = [(h, a) for h, a in fixtures if h < size and a < size]
                if not pairs:
                    continue
                if len(self.startList.groups) > 1:
                    lines.append(i.name)
                for home, away in pairs:
                    lines.append(self._formatFixture(i.athletes[home], i.athletes[away]))
            lines.append("")
        return "\n".join(lines)

    def supportsOdds(self):
        return self._oddsParadigm() is not None

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        groupSize = self.largestGroupSize(self.startList)
        if p is None or groupSize == 0:
            return None

        fixtures = self.generateFixtures(matchday, groupSize)
        lines = []
        for i in self.startList.groups:
            size = len(i.athletes)
            pairs = [(h, a) for h, a in fixtures if h < size and a < size]
            if not pairs:
                continue
            if len(self.startList.groups) > 1:
                lines.append(i.name)
            for home, away in pairs:
                lines.append(self._formatOdds(p, i.athletes[home], i.athletes[away], trials))
        return "\n".join(lines) + ("\n" if lines else "")

    def generateTableColumns(self, groupName):
        from xkoranate.tablegenerator.tablecolumn import XkorTableColumn

        columns = []

        nameWidth = self.nameWidth()
        if len(groupName) > nameWidth:
            nameWidth = len(groupName)
        matchdayWidth = int(math.log10(self.matchdays())) + 1
        positionWidth = int(math.log10(self.largestGroupSize(self.startList))) + 1
        opt = self.sport.paradigmOptions()

        sortCriteria = self.tableSortCriteria()
        usesGoalAverage = "goalAverage" in sortCriteria
        usesGoalDifference = "goalDifference" in sortCriteria
        usesGoalsAgainst = "goalsAgainst" in sortCriteria
        usesGoalsFor = "goalsFor" in sortCriteria
        usesWinPercent = "winPercent" in sortCriteria
        usesWinPercentPure = "winPercentPure" in sortCriteria
        usesWinPercentNFL = "winPercentNFL" in sortCriteria
        usesPoints = "points" in sortCriteria

        columns.append(XkorTableColumn("position", "", positionWidth))
        columns.append(XkorTableColumn("name", groupName, nameWidth))
        columns.append(XkorTableColumn("played", toString(opt.get("tableHeaderPlayed", "Pld")), matchdayWidth + 2))
        columns.append(XkorTableColumn("wins", toString(opt.get("tableHeaderWins", "W")), matchdayWidth + 2))
        if toString(opt.get("forceTieBreak")) != "1" and toString(self.userOpt.get("allowDraws")) != "false":
            columns.append(XkorTableColumn("draws", toString(opt.get("tableHeaderDraws", "D")), matchdayWidth + 1))
        columns.append(XkorTableColumn("losses", toString(opt.get("tableHeaderLosses", "L")), matchdayWidth + 1))
        if usesGoalAverage or usesGoalDifference or usesGoalsAgainst or usesGoalsFor:
            columns.append(XkorTableColumn("goalsFor", toString(opt.get("tableHeaderGoalsFor", "PF")), matchdayWidth + 3))
            columns.append(XkorTableColumn("goalsAgainst", toString(opt.get("tableHeaderGoalsAgainst", "PA")), matchdayWidth + 2))
        if usesGoalAverage:
            columns.append(XkorTableColumn("goalAverage", toString(opt.get("tableHeaderGoalAverage", "Avg")), 7))
        if usesGoalDifference:
            columns.append(XkorTableColumn("goalDifference", toString(opt.get("tableHeaderGoalDifference", "PD")), matchdayWidth + 2))
        if usesWinPercent:
            columns.append(XkorTableColumn("winPercent", toString(opt.get("tableHeaderWinPercent", "Win %")), 8))
        if usesWinPercentPure:
            columns.append(XkorTableColumn("winPercentPure", toString(opt.get("tableHeaderWinPercent", "Win %")), 8))
        if usesWinPercentNFL:
            columns.append(XkorTableColumn("winPercentNFL", toString(opt.get("tableHeaderWinPercent", "Win %")), 8))
        if usesPoints:
            columns.append(XkorTableColumn("points", toString(opt.get("tableHeaderPoints", "Pts")), matchdayWidth + 3))
        if toString(self.userOpt.get("showResultsGrid")) == "true":
            columns.append(XkorTableColumn("resultsGrid", "", self.largestGroupSize(self.startList) * 5))

        return columns

    def largestGroupSize(self, sl):
        rval = 0
        for i in sl.groups:
            if len(i.athletes) > rval:
                rval = len(i.athletes)
        if rval & 1:
            rval += 1  # rval should be even
        return rval

    def matchdays(self):
        if "numberOfLegs" in self.userOpt:
            return toInt(self.userOpt.get("numberOfLegs")) * (self.largestGroupSize(self.startList) - 1)
        else:
            return self.largestGroupSize(self.startList) - 1

    def matchdayNames(self):
        rval = []
        for i in range(self.matchdays()):
            rval.append("Matchday " + str(i + 1))
        return rval

    def retrieveMatches(self, groupNo, upTo=None):
        """The saved matches for a group; with `upTo`, only those played on
        that matchday or earlier."""
        from xkoranate.tablegenerator.tablematch import XkorTableMatch

        rval = []

        if "tableData" in self.userOpt:
            tableData = toList(self.userOpt.get("tableData"))
            if len(tableData) > groupNo:
                results = toList(tableData[groupNo])
                for i in results:
                    # match scores of form “1: Aquilla 3–1 Busby”, with an optional
                    # “OT”/“SO” decider marker before the away team, e.g. “1: Aquilla 3–1 OT Busby”.
                    # A score can be negative (taekwondo deducts penalty points), “1: Aquilla 6–-1 Busby”
                    rx = re.search("([0-9]+): (.+) (-?[0-9.]+)–(-?[0-9.]+)(?: (OT|SO))? (.+)", toString(i))
                    if rx is not None:  # if we matched
                        if upTo is not None and int(rx.group(1)) > upTo:
                            continue
                        rval.append(XkorTableMatch(rx.group(2), rx.group(6), toDouble(rx.group(3)), toDouble(rx.group(4)), rx.group(5)))
        return rval

    def revertToMatchday(self, matchday):
        # “matchday” is the first that will be erased
        # delete the results
        for k in list(self.resultsBuf.keys()):
            if k >= matchday:
                self.resultsBuf[k] = ""

        # sort out the table data
        tableData = toList(self.userOpt.get("tableData"))
        for idx in range(len(tableData)):
            groupData = toList(tableData[idx])
            for j in range(len(groupData)):
                rx = re.search("([0-9]+): (.+ -?[0-9.]+–-?[0-9.]+ .+)", toString(groupData[j]))  # find out what matchday the score is from
                if rx is not None and toDouble(rx.group(1)) >= matchday:  # if it’s on “matchday” or later…
                    groupData[j] = ""  # …blank the value
            # actually delete the blanked values
            groupData = [x for x in groupData if x != ""]
            tableData[idx] = groupData
        self.resumeOpt["tableData"] = tableData
        return dict(self.resumeOpt)

    def scorinateMatchday(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()

        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

        fixtures = self.generateFixtures(matchday, self.largestGroupSize(self.startList))

        tableData = toList(self.resumeOpt.get("tableData"))

        # make sure we have a place to insert matches to
        while len(tableData) < len(self.startList.groups):
            tableData.append([])

        groupNo = 0
        for i in self.startList.groups:
            athletes = []
            groupData = toList(tableData[groupNo])
            groupSize = len(i.athletes)

            for j in fixtures:
                if j[0] < groupSize and j[1] < groupSize:
                    athletes.append(i.athletes[j[0]])
                    athletes.append(i.athletes[j[1]])

            p.scorinate(athletes)

            if toString(self.userOpt.get("allowDraws")) == "false":
                # if there’s a tie, deal with it
                results = list(p.results())
                for j in range(0, len(results) - (len(results) % 2), 2):
                    score1 = results[j]
                    score2 = results[j + 1]
                    if p.compare(score1, score2) == 0:
                        tiebreakAthletes = [score1.athlete, score2.athlete]
                        p.breakTie(tiebreakAthletes)

            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + i.name + "\n" + p.output() + "\n"

            # assemble teh tablez
            for j in fixtures:
                if j[0] < groupSize and j[1] < groupSize:
                    score1 = p.findResult(i.athletes[j[0]].id)
                    score2 = p.findResult(i.athletes[j[1]].id)

                    scoreValue1, scoreValue2, decider = self.tableScores(
                        p, score1, score2, toString(self.userOpt.get("allowDraws")) != "false")
                    self.tables[groupNo].insertMatch(i.athletes[j[0]].name, i.athletes[j[1]].name, scoreValue1, scoreValue2, decider)

                    # insert into the resume options
                    deciderSuffix = (" " + decider) if decider else ""
                    groupData.append(str(matchday) + ": " + i.athletes[j[0]].name + " " + qNumber(scoreValue1) + "–" + qNumber(scoreValue2) + deciderSuffix + " " + i.athletes[j[1]].name)

            self.tables[groupNo].generate()
            tableData[groupNo] = groupData
            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + self.tables[groupNo].toText()
            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + "\n"

            groupNo += 1
        self.resumeOpt["tableData"] = tableData

    def _newTable(self, groupName, matches):
        """A group's standings table holding `matches`. Both scorinating and
        formatQualifications() build tables through here, so the latter can
        recognise the table text the former wrote."""
        from xkoranate.tablegenerator.table import XkorTable

        t = XkorTable()
        t.setColumns(self.generateTableColumns(groupName))
        t.setMatches(matches)
        self._configureTable(t, self.tableSortCriteria())
        return t

    def _configureTable(self, t, sortCriteria):
        t.setSortCriteria(sortCriteria)
        t.setPointsForWin(toInt(self.userOpt.get("pointsForWin")) if "pointsForWin" in self.userOpt else 3)
        t.setPointsForDraw(toInt(self.userOpt.get("pointsForDraw")) if "pointsForDraw" in self.userOpt else 1)
        t.setPointsForLoss(toInt(self.userOpt.get("pointsForLoss")) if "pointsForLoss" in self.userOpt else 0)
        # OT/SO points are left unset (falling back to win/loss) unless the
        # competition explicitly overrides them, so existing events score unchanged
        if "pointsForOTWin" in self.userOpt:
            t.setPointsForOTWin(toInt(self.userOpt.get("pointsForOTWin")))
        if "pointsForSOWin" in self.userOpt:
            t.setPointsForSOWin(toInt(self.userOpt.get("pointsForSOWin")))
        if "pointsForOTLoss" in self.userOpt:
            t.setPointsForOTLoss(toInt(self.userOpt.get("pointsForOTLoss")))
        if "pointsForSOLoss" in self.userOpt:
            t.setPointsForSOLoss(toInt(self.userOpt.get("pointsForSOLoss")))

    def supportsQualifications(self):
        return True

    def formatQualifications(self, text, matchday, settings):
        from xkoranate.competitions.qualification import leagueMarkers

        if not text or not settings.isEnabled() or self.largestGroupSize(self.startList) == 0:
            return text
        key = (text, matchday, settings)
        if key in self._qualificationCache:
            return self._qualificationCache[key]

        # the standings as they stood after `matchday`, rebuilt from the
        # saved matches — the same way scorinate() built them
        groups = self.startList.groups
        tables = []
        for groupNo, g in enumerate(groups):
            t = self._newTable(g.name, self.retrieveMatches(groupNo, upTo=matchday))
            t.generate()
            tables.append(t)

        markers = leagueMarkers(
            [self._qualificationGroup(g, t, matchday) for g, t in zip(groups, tables)],
            settings, crossRank=lambda candidates: self._rankNextPlaced(candidates, tables))

        rval = text
        if any(markers):
            for t, m in zip(tables, markers):
                plain = t.toText()
                if plain not in rval:
                    # the stored table isn't the one these matches give (saved
                    # by an older version, or a coin flip re-rolled): leave it
                    continue
                t.setColumns(self._withQualificationColumn(t.getColumns()))
                t.setMarkers(m)
                rval = rval.replace(plain, t.toText(), 1)
        self._qualificationCache[key] = rval
        return rval

    def _qualificationGroup(self, group, table, matchday):
        from xkoranate.competitions.qualification import QualificationGroup

        names = [a.name for a in group.athletes]
        size = len(names)
        remaining = []
        groupSize = self.largestGroupSize(self.startList)
        for md in range(matchday + 1, self.matchdays()):
            for home, away in self.generateFixtures(md, groupSize):
                if home < size and away < size:
                    remaining.append((names[home], names[away]))

        rows = [r for b in table.data for r in b]
        metric, outcomes, scale = self._qualificationMetric(table, size)
        current = None if metric is None else {r.name(): metric(r) for r in rows}
        return QualificationGroup(
            teams=names, current=current, remaining=remaining,
            outcomes=outcomes, order=[[r.name() for r in b] for b in table.data if b],
            scale=scale)

    def _qualificationMetric(self, table, groupSize):
        """How the table's first sort criterion is earned, as (value of a row,
        what one match can add to each side, scale), or Nones when it can't
        be projected forward. Win percentages are compared as totals within
        a group and divided by games played across groups."""
        from fractions import Fraction

        criteria = self.tableSortCriteria()
        first = criteria[0] if criteria else ""
        draws = (toString(self.sport.paradigmOptions().get("forceTieBreak")) != "1"
                 and toString(self.userOpt.get("allowDraws")) != "false")
        legs = toInt(self.userOpt.get("numberOfLegs")) if "numberOfLegs" in self.userOpt else 1
        perGame = Fraction(1, max(1, (groupSize - 1) * legs))
        win = [(1, 0), (0, 1)]  # one side wins, the other loses

        if first == "points":
            w, d, l = table.getPointsForWin(), table.getPointsForDraw(), table.getPointsForLoss()
            outcomes = [(w, l), (l, w)]
            if draws:
                outcomes.append((d, d))
            else:  # a level match goes to extra time or a shootout instead
                for winPts, lossPts in ((table.getPointsForOTWin(), table.getPointsForOTLoss()),
                                        (table.getPointsForSOWin(), table.getPointsForSOLoss())):
                    outcomes += [(winPts, lossPts), (lossPts, winPts)]
            return (lambda r: Fraction(table.getPoints(r))), outcomes, Fraction(1)
        if first == "wins":
            return (lambda r: Fraction(r.wins())), win + ([(0, 0)] if draws else []), Fraction(1)
        if first == "winPercent":
            half = Fraction(1, 2)
            return ((lambda r: Fraction(r.wins()) + Fraction(r.draws()) / 2),
                    win + ([(half, half)] if draws else []), perGame)
        if first == "winPercentPure":
            return (lambda r: Fraction(r.wins())), win + ([(0, 0)] if draws else []), perGame
        if first == "winPercentNFL" and not draws:
            return (lambda r: Fraction(r.wins())), win, perGame
        return None, None, Fraction(1)

    def _rankNextPlaced(self, candidates, tables):
        """Rank the teams placed X+1 in different groups against each other
        with the table's own sort rules, leaving out the head-to-head ones
        (they never met) and coin flips."""
        from xkoranate.tablegenerator.table import XkorTable

        sorter = XkorTable()
        self._configureTable(sorter, [c for c in self.tableSortCriteria()
                                      if not c.startswith("h2h") and c != "coinFlip"])
        rows = []
        owner = {}
        for groupNo, name in candidates:
            row = next((r for b in tables[groupNo].data for r in b if r.name() == name), None)
            if row is None:
                return None
            row = row.clone()
            rows.append(row)
            owner[id(row)] = (groupNo, name)
        return [[owner[id(r)] for r in b] for b in sorter.sortTable(rows) if b]

    @staticmethod
    def _withQualificationColumn(columns):
        """The marker column goes straight after the points (before a
        results grid), with a blank heading."""
        from xkoranate.tablegenerator.tablecolumn import XkorTableColumn

        types = [c.columnType for c in columns]
        if "points" in types:
            at = types.index("points") + 1
        elif "resultsGrid" in types:
            at = types.index("resultsGrid")
        else:
            at = len(columns)
        return columns[:at] + [XkorTableColumn("qualification", "", 1)] + columns[at:]

    def tableSortCriteria(self):
        rval = []

        if "sortCriteria" in self.userOpt:
            criteria = toList(self.userOpt.get("sortCriteria"))
            for i in criteria:
                rval.append(toString(i))
        else:
            from xkoranate.tablegenerator.sortcriteriawidget import XkorSortCriteriaWidget

            rval = XkorSortCriteriaWidget.defaultSortCriteria()
        return rval
