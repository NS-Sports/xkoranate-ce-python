import math
import re

from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.variant import qNumber, toDouble, toInt, toList, toString, toUInt


class XkorRoundRobinCompetition(XkorAbstractCompetition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tables = []  # QList<XkorTable>

    def hasOptionsWidget(self):
        return True

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.roundrobincompetitionoptions import XkorRoundRobinCompetitionOptions

        return XkorRoundRobinCompetitionOptions(competitionOptions)

    def scorinate(self, matchday):
        from xkoranate.tablegenerator.table import XkorTable

        if self.largestGroupSize(self.startList) > 0:  # if there are no teams, don’t bother!
            # initialize the tables
            self.tables = []
            sortCriteria = self.tableSortCriteria()
            groupNo = 0
            for i in self.startList.groups:
                t = XkorTable()
                t.setColumns(self.generateTableColumns(i.name))
                t.setMatches(self.retrieveMatches(groupNo))
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
                self.tables.append(t)
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

    def retrieveMatches(self, groupNo):
        from xkoranate.tablegenerator.tablematch import XkorTableMatch

        rval = []

        if "tableData" in self.userOpt:
            tableData = toList(self.userOpt.get("tableData"))
            if len(tableData) > groupNo:
                results = toList(tableData[groupNo])
                for i in results:
                    # match scores of form “1: Aquilla 3–1 Busby”, with an optional
                    # “OT”/“SO” decider marker before the away team, e.g. “1: Aquilla 3–1 OT Busby”
                    rx = re.search("[0-9]+: (.+) ([0-9.]+)–([0-9.]+)(?: (OT|SO))? (.+)", toString(i))
                    if rx is not None:  # if we matched
                        rval.append(XkorTableMatch(rx.group(1), rx.group(5), toDouble(rx.group(2)), toDouble(rx.group(3)), rx.group(4)))
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
                rx = re.search("([0-9]+): (.+ [0-9.]+–[0-9.]+ .+)", toString(groupData[j]))  # find out what matchday the score is from
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

                    # with draws allowed a tie is a result in its own right,
                    # so the tiebreaker stages don't come into the table
                    if toString(self.userOpt.get("allowDraws")) == "false":
                        scoreValue1, scoreValue2, decider = self.effectiveScores(p, score1, score2)
                    else:
                        scoreValue1, scoreValue2, decider = score1.score(), score2.score(), None
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
