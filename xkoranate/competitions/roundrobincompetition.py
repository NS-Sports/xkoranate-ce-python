import math
import re

from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.variant import qNumber, toDouble, toInt, toList, toString, toUInt

# a saved result: “3: Aquilla 3–1 Busby”, with an optional “OT”/“SO” decider
# marker before the away team, e.g. “3: Aquilla 3–1 OT Busby”. A score can be
# negative (taekwondo deducts penalty points), e.g. “3: Aquilla 6–-1 Busby”
_STORED_MATCH = re.compile("([0-9]+): (.+) (-?[0-9.]+)–(-?[0-9.]+)(?: (OT|SO))? (.+)")


# column type -> (sport option naming its heading, default heading)
_TABLE_HEADINGS = {
    "played": ("tableHeaderPlayed", "Pld"),
    "wins": ("tableHeaderWins", "W"),
    "draws": ("tableHeaderDraws", "D"),
    "losses": ("tableHeaderLosses", "L"),
    "goalsFor": ("tableHeaderGoalsFor", "PF"),
    "goalsAgainst": ("tableHeaderGoalsAgainst", "PA"),
    "goalAverage": ("tableHeaderGoalAverage", "Avg"),
    "goalDifference": ("tableHeaderGoalDifference", "PD"),
    "winPercent": ("tableHeaderWinPercent", "Win %"),
    "winPercentPure": ("tableHeaderWinPercent", "Win %"),
    "winPercentNFL": ("tableHeaderWinPercent", "Win %"),
    "points": ("tableHeaderPoints", "Pts"),
}


# the points a round robin awards when its options don't say
DEFAULT_POINTS = (("pointsForWin", 3), ("pointsForDraw", 1), ("pointsForLoss", 0))


def intOption(options, key, default):
    """options[key] as an int, or `default` if it isn't set."""
    return toInt(options.get(key)) if key in options else default


def tablePoints(options):
    """(win, draw, loss) points from competition options."""
    return tuple(intOption(options, key, default) for key, default in DEFAULT_POINTS)


def parseStoredMatch(line):
    """(matchday, XkorTableMatch) from a saved result line, or None."""
    from xkoranate.tablegenerator.tablematch import XkorTableMatch

    rx = _STORED_MATCH.search(toString(line))
    if rx is None:
        return None
    return (int(rx.group(1)),
            XkorTableMatch(rx.group(2), rx.group(6), toDouble(rx.group(3)), toDouble(rx.group(4)), rx.group(5)))


def formatStoredMatch(matchday, home, away, score1, score2, decider=None):
    """The saved form of a result, as parseStoredMatch reads it back."""
    deciderSuffix = (" " + decider) if decider else ""
    return str(matchday) + ": " + home + " " + qNumber(score1) + "–" + qNumber(score2) + deciderSuffix + " " + away


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
                self.tables.append(self._groupTable(i.name, self.retrieveMatches(groupNo)))
                groupNo += 1

            # initialize the results in the resume file options
            self.resumeOpt["tableData"] = self.userOpt.get("tableData")

            numberOfLegs = 1
            if "numberOfLegs" in self.userOpt:
                numberOfLegs = toUInt(self.userOpt.get("numberOfLegs"))  # noqa: F841 (unused in the C++ too)

            self.scorinateMatchday(matchday)
            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + "\n"

    @staticmethod
    def generateFixtures(matchday, groupSize):
        """(home, away) index pairs for one matchday of a round robin of
        groupSize (even) teams, circle method; later legs swap home and away."""
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

    @staticmethod
    def groupPairs(fixtures, size):
        """The (home, away) index pairs a group of `size` teams plays, out of
        fixtures made for the largest group."""
        return [(h, a) for h, a in fixtures if h < size and a < size]

    def _groupFixtures(self, matchday, groupSize):
        """(group name, fixtures) for each group on one matchday."""
        fixtures = self.generateFixtures(matchday, groupSize)
        return [(g.name, [(g.athletes[h], g.athletes[a]) for h, a in self.groupPairs(fixtures, len(g.athletes))])
                for g in self.startList.groups]

    def schedule(self):
        groupSize = self.largestGroupSize(self.startList)
        if groupSize == 0:
            return None

        matchdayNames = self.matchdayNames()
        lines = []
        for matchday in range(self.matchdays()):
            lines.append(matchdayNames[matchday])
            lines += self._fixtureLines(self._groupFixtures(matchday, groupSize), self._formatFixture,
                                        len(self.startList.groups) > 1)
            lines.append("")
        return "\n".join(lines)

    def supportsOdds(self):
        return self._oddsParadigm() is not None

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        groupSize = self.largestGroupSize(self.startList)
        if p is None or groupSize == 0:
            return None

        return self._oddsText(self._fixtureLines(
            self._groupFixtures(matchday, groupSize),
            lambda home, away: self._formatOdds(p, home, away, trials),
            len(self.startList.groups) > 1))

    def setTablePoints(self, t):
        win, draw, loss = tablePoints(self.userOpt)
        t.setPointsForWin(win)
        t.setPointsForDraw(draw)
        t.setPointsForLoss(loss)
        # OT/SO points are left unset (falling back to win/loss) unless the
        # competition explicitly overrides them, so existing events score unchanged
        for name in ("OTWin", "SOWin", "OTLoss", "SOLoss"):
            if "pointsFor" + name in self.userOpt:
                getattr(t, "setPointsFor" + name)(toInt(self.userOpt.get("pointsFor" + name)))

    def generateTableColumns(self, groupName, teamCount=None):
        from xkoranate.tablegenerator.tablecolumn import standingsColumns

        nameWidth = self.nameWidth()
        if len(groupName) > nameWidth:
            nameWidth = len(groupName)
        matchdayWidth = int(math.log10(self.matchdays())) + 1
        positionWidth = int(math.log10(teamCount or self.largestGroupSize(self.startList))) + 1
        opt = self.sport.paradigmOptions()

        def heading(columnType):
            key, default = _TABLE_HEADINGS[columnType]
            return toString(opt.get(key, default))

        return standingsColumns(
            self.tableSortCriteria(), heading, groupName, nameWidth, positionWidth, matchdayWidth,
            draws=toString(opt.get("forceTieBreak")) != "1" and self.allowsDraws(),
            gridWidth=(self.largestGroupSize(self.startList) * 5
                       if toString(self.userOpt.get("showResultsGrid")) == "true" else None))

    def largestGroupSize(self, sl):
        rval = 0
        for i in sl.groups:
            if len(i.athletes) > rval:
                rval = len(i.athletes)
        if rval & 1:
            rval += 1  # rval should be even
        return rval

    def matchdays(self):
        return intOption(self.userOpt, "numberOfLegs", 1) * (self.largestGroupSize(self.startList) - 1)

    def matchdayNames(self):
        rval = []
        for i in range(self.matchdays()):
            rval.append("Matchday " + str(i + 1))
        return rval

    def retrieveMatches(self, groupNo, upTo=None):
        """The saved matches for a group; with `upTo`, only those played on
        that matchday or earlier."""
        rval = []

        if "tableData" in self.userOpt:
            tableData = toList(self.userOpt.get("tableData"))
            if len(tableData) > groupNo:
                results = toList(tableData[groupNo])
                for i in results:
                    parsed = parseStoredMatch(i)
                    if parsed is not None:  # if we matched
                        if upTo is not None and parsed[0] > upTo:
                            continue
                        rval.append(parsed[1])
        return rval

    def revertToMatchday(self, matchday):
        # “matchday” is the first that will be erased
        self._clearResultsFrom(matchday)

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
        p = self._newParadigm()

        fixtures = self.generateFixtures(matchday, self.largestGroupSize(self.startList))

        tableData = toList(self.resumeOpt.get("tableData"))

        # make sure we have a place to insert matches to
        while len(tableData) < len(self.startList.groups):
            tableData.append([])

        groupNo = 0
        for i in self.startList.groups:
            athletes = []
            groupData = toList(tableData[groupNo])
            pairs = self.groupPairs(fixtures, len(i.athletes))

            for home, away in pairs:
                athletes.append(i.athletes[home])
                athletes.append(i.athletes[away])

            p.scorinate(athletes)

            if not self.allowsDraws():
                # if there’s a tie, deal with it
                self._breakDrawnPairs(p)

            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + i.name + "\n" + p.output() + "\n"

            # assemble teh tablez
            for home, away in pairs:
                score1 = p.findResult(i.athletes[home].id)
                score2 = p.findResult(i.athletes[away].id)

                scoreValue1, scoreValue2, decider = self.tableScores(
                    p, score1, score2, self.allowsDraws())
                self.tables[groupNo].insertMatch(i.athletes[home].name, i.athletes[away].name, scoreValue1, scoreValue2, decider)

                # insert into the resume options
                groupData.append(formatStoredMatch(matchday, i.athletes[home].name, i.athletes[away].name, scoreValue1, scoreValue2, decider))

            self.tables[groupNo].generate()
            tableData[groupNo] = groupData
            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + self.tables[groupNo].toText()
            self.resultsBuf[matchday] = self.resultsBuf.get(matchday, "") + "\n"

            groupNo += 1
        self.resumeOpt["tableData"] = tableData

    def _groupTable(self, groupName, matches):
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
        self.setTablePoints(t)

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
        tables = [self._rebuilt(text, self._groupTable(g.name, self.retrieveMatches(groupNo, upTo=matchday)))
                  for groupNo, g in enumerate(groups)]

        markers = leagueMarkers(
            [self._qualificationGroup(g, t, matchday) for g, t in zip(groups, tables)],
            settings, crossRank=lambda candidates: self._rankNextPlaced(candidates, tables))

        rval = self._markTables(text, list(zip(tables, markers)))
        self._qualificationCache[key] = rval
        return rval

    def _rebuilt(self, text, t):
        """Generate a table rebuilt for formatQualifications()."""
        if "coinFlip" in t.getSortCriteria():
            # league tables don't save their coin flips, so rebuilding
            # one re-rolls any tie a flip decided; take the flips from
            # the order the stored table shows instead
            t.setCoinFlips(self._storedFlips(text, t))
        t.generate()
        return t

    def _markTables(self, text, tablesAndMarkers):
        """Swap each table's plain text in `text` for one with a marker
        column. Every table gets the column once any team has a marker."""
        if not any(m for _t, m in tablesAndMarkers):
            return text
        for t, m in tablesAndMarkers:
            plain = t.toText()
            if plain not in text:
                # the stored table isn't the one these matches give (saved
                # by an older version, or edited): leave it
                continue
            t.setColumns(self._withQualificationColumn(t.getColumns()))
            t.setMarkers(m)
            text = text.replace(plain, t.toText(), 1)
        return text

    @staticmethod
    def _storedFlips(text, table):
        """Coin-flip values that reproduce the row order of `table` as it
        appears in the stored results text: earlier rows flip higher. Empty
        if the table can't be found there."""
        columns = table.getColumns()
        if len(columns) < 2 or columns[0].columnType != "position":
            return {}
        header = table.toText().split("\n")[0]  # doesn't depend on the order
        lines = text.split("\n")
        if header not in lines:
            return {}
        start = columns[0].width + 1  # where the name column begins
        names = sorted(table.unsortedData.keys(), key=len, reverse=True)
        flips = {}
        rows = lines[lines.index(header) + 1:]
        for i, row in enumerate(rows):
            if not row.strip():
                break
            for name in names:
                if name not in flips and row[start:start + len(name)] == name:
                    flips[name] = len(rows) - i
                    break
        return flips

    def _qualificationGroup(self, group, table, matchday):
        from xkoranate.competitions.qualification import QualificationGroup

        names = [a.name for a in group.athletes]
        size = len(names)
        remaining = []
        groupSize = self.largestGroupSize(self.startList)
        for md in range(matchday + 1, self.matchdays()):
            for home, away in self.groupPairs(self.generateFixtures(md, groupSize), size):
                remaining.append((names[home], names[away]))

        legs = intOption(self.userOpt, "numberOfLegs", 1)
        metric, outcomes, scale = self._qualificationMetric(table, (size - 1) * legs)
        return QualificationGroup(
            teams=names, current=self._currentMetric(table, metric), remaining=remaining,
            outcomes=None if outcomes is None else outcomes(False),
            order=[[r.name() for r in b] for b in table.data if b], scale=scale)

    @staticmethod
    def _currentMetric(table, metric):
        if metric is None:
            return None
        return {r.name(): metric(r) for b in table.data for r in b}

    def _qualificationMetric(self, table, gamesPerTeam):
        """How the table's first sort criterion is earned, as (value of a
        row, outcomes(cross) giving what one match can add to each side,
        scale), or Nones when it can't be projected forward. `cross` asks
        about a game against another conference, which can score its own
        points. Win percentages are compared as totals within a group and
        divided by games per team across groups (`gamesPerTeam`, None if it
        isn't the same for everyone)."""
        from fractions import Fraction

        criteria = self.tableSortCriteria()
        first = criteria[0] if criteria else ""
        draws = (toString(self.sport.paradigmOptions().get("forceTieBreak")) != "1"
                 and self.allowsDraws())
        perGame = None if not gamesPerTeam else Fraction(1, gamesPerTeam)
        win = [(1, 0), (0, 1)]  # one side wins, the other loses

        if first == "points":
            def outcomes(cross):
                w, d, l = table.getPointsForWin(), table.getPointsForDraw(), table.getPointsForLoss()
                cross = cross and table.crossPoints is not None
                if cross:
                    w, d, l = table.crossPoints
                rval = [(w, l), (l, w)]
                if draws:
                    rval.append((d, d))
                    return rval
                # a level match goes to extra time or a shootout instead; in
                # a cross game those follow the cross points unless set
                for winRaw, winPts, lossRaw, lossPts in (
                        (table.getRawPointsForOTWin(), table.getPointsForOTWin(),
                         table.getRawPointsForOTLoss(), table.getPointsForOTLoss()),
                        (table.getRawPointsForSOWin(), table.getPointsForSOWin(),
                         table.getRawPointsForSOLoss(), table.getPointsForSOLoss())):
                    winPts = w if cross and winRaw is None else winPts
                    lossPts = l if cross and lossRaw is None else lossPts
                    rval += [(winPts, lossPts), (lossPts, winPts)]
                return rval
            return (lambda r: Fraction(table.getPoints(r))), outcomes, Fraction(1)

        plain = win + ([(0, 0)] if draws else [])
        if first == "wins":
            return (lambda r: Fraction(r.wins())), (lambda cross: plain), Fraction(1)
        if perGame is None:
            return None, None, Fraction(1)
        if first == "winPercent":
            half = Fraction(1, 2)
            withHalves = win + ([(half, half)] if draws else [])
            return ((lambda r: Fraction(r.wins()) + Fraction(r.draws()) / 2),
                    (lambda cross: withHalves), perGame)
        if first == "winPercentPure":
            return (lambda r: Fraction(r.wins())), (lambda cross: plain), perGame
        if first == "winPercentNFL" and not draws:
            return (lambda r: Fraction(r.wins())), (lambda cross: win), perGame
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
