from ..variant import qNumber
from .pointsscheme import XkorPointsAccessors, XkorPointsScheme
from .tablematch import XkorTableMatch
from .tablerow import XkorTableRow
from .tablesorter import XkorTableSorter

# columns showing the XkorTableRow count of the same name
_COUNT_COLUMNS = frozenset(("played", "wins", "draws", "losses", "otWins", "soWins",
                            "otLosses", "soLosses", "goalsFor", "goalsAgainst"))


class XkorTable(XkorPointsAccessors):
    def __init__(self):
        self.tableName = ""
        self.columns = []
        self.matches = []
        self.unsortedData = {}  # QHash<QString, XkorTableRow>
        self.data = []
        self.sortCriteria = []
        self.points = XkorPointsScheme()
        self.sorter = XkorTableSorter(self.points)
        self.columnWidth = 0
        self.showDraws = False
        self.showResultsGrid = False
        self.showOvertime = False
        self.goalName = ""
        # None shows every team that has played; a list limits the table to
        # those teams, e.g. one conference's standings built from matches
        # that include its games against other conferences
        self.teams = None
        # team name -> conference; with crossPoints set, games between teams
        # of different conferences score (win, draw, loss) = crossPoints
        self.conferences = {}
        # team name -> "Q"/"E", shown in a "qualification" column if the
        # columns include one (see XkorRoundRobinCompetition.formatQualifications)
        self.markers = {}

    def isCross(self, team1, team2):
        c1 = self.conferences.get(team1)
        c2 = self.conferences.get(team2)
        return c1 is not None and c2 is not None and c1 != c2

    def addMatchToData(self, m):
        cross = self.isCross(m.team1, m.team2)
        i = self.findTeam(m.team1)
        i.insertMatch(m.team2, m.score1, m.score2, True, m.decider, cross)
        i = self.findTeam(m.team2)
        i.insertMatch(m.team1, m.score2, m.score1, False, m.decider, cross)

    def collapse(self, target, source):
        for i in source:
            target.append(i)

    def findTeam(self, name):
        rval = self.unsortedData.get(name)
        if rval is None:
            rval = XkorTableRow(name)
            self.unsortedData[name] = rval
        return rval

    def generate(self):
        self.data = []

        shown = [name for name in self.unsortedData
                 if self.teams is None or name in self.teams]
        oldData = []
        for name in shown:
            oldData.append(self.unsortedData[name].clone())

        if shown:
            # guarded: generating an empty table (no results entered yet)
            # shouldn't throw away the flips of a table that has them
            self.sorter.pruneCoinFlips(shown)

        self.collapse(self.data, self.sortTable(oldData))

    @property
    def crossPoints(self):
        return self.points.cross

    def getPoints(self, a):
        return self.points.pointsFor(a)

    def getColumns(self):
        return list(self.columns)

    def getMatches(self):
        return list(self.matches)

    def getCoinFlips(self):
        return dict(self.sorter.getCoinFlips())

    def getColumnWidth(self):
        return self.columnWidth

    def getGoalName(self):
        return self.goalName

    def getShowDraws(self):
        return self.showDraws

    def getShowOvertime(self):
        return self.showOvertime

    def getShowResultsGrid(self):
        return self.showResultsGrid

    def getSortCriteria(self):
        return list(self.sortCriteria)

    def insertMatch(self, m, t2=None, score1=None, score2=None, decider=None):
        if t2 is not None:
            m = XkorTableMatch(m, t2, score1, score2, decider)
        self.matches.append(m)
        self.addMatchToData(m)

    def setCoinFlips(self, flips):
        self.sorter.setCoinFlips(dict(flips))

    def setColumns(self, c):
        self.columns = list(c)

    def setColumnWidth(self, width):
        self.columnWidth = width

    def setGoalName(self, name):
        self.goalName = name

    def setMarkers(self, markers):
        self.markers = dict(markers)

    def setMatches(self, m):
        self.matches = list(m)
        self.updateMatches()

    def setConferences(self, conferences):
        """Which conference each team is in; set before adding matches."""
        self.conferences = dict(conferences)
        self.updateMatches()

    def setTeams(self, names):
        """Limit the table to these teams; None shows everyone."""
        self.teams = None if names is None else set(names)

    def setShowDraws(self, value):
        self.showDraws = value

    def setShowOvertime(self, value):
        self.showOvertime = value

    def setShowResultsGrid(self, value):
        self.showResultsGrid = value

    def setSortCriteria(self, sc):
        self.sortCriteria = list(sc)

    def sortTable(self, rows):
        rval = []

        if len(rows) > 0:
            for i in self.sortCriteria:
                sortedRows = self.sorter.sort(rows, i)
                if len(sortedRows) > 1:
                    for j in sortedRows:
                        self.collapse(rval, self.sortTable(j))
                    return rval

            # if the teams are tied
            sortedRows = self.sorter.sort(rows, "alphabetical")
            rval.append(sortedRows[0])
        else:
            rval.append([])
        return rval

    def toText(self):
        rval = ""

        # header
        for k in self.columns:
            if k.columnType == "name":
                rval += k.heading.ljust(k.width)
            else:
                rval += k.heading.rjust(k.width)
            rval += " "
        rval += "\n"

        rank = 1
        acc = 1
        for i in self.data:
            for j in i:
                for kIndex, k in enumerate(self.columns):
                    if kIndex != 0:
                        rval += " "
                    if k.columnType == "position":
                        if rank == acc:
                            rval += str(rank).rjust(k.width)
                        else:
                            rval += " " * k.width
                    elif k.columnType == "name":
                        rval += j.name().ljust(k.width)
                    elif k.columnType in _COUNT_COLUMNS:
                        rval += qNumber(getattr(j, k.columnType)()).rjust(k.width)
                    elif k.columnType == "goalDifference":
                        rval += (("+" if j.goalDifference() > 0
                                  else ("−" if j.goalDifference() < 0 else ""))
                                 + str(abs(int(j.goalDifference())))).rjust(k.width)
                    elif k.columnType == "goalAverage":
                        rval += ("∞" if j.goalsAgainst() == 0
                                 else "%.3f" % (j.goalsFor() / j.goalsAgainst())).rjust(k.width)
                    elif k.columnType == "points":
                        rval += qNumber(self.getPoints(j)).rjust(k.width)
                    elif k.columnType == "qualification":
                        rval += self.markers.get(j.name(), "").ljust(k.width)
                    elif k.columnType == "winPercent":
                        rval += ("undef" if j.played() == 0
                                 else "%.3f" % ((j.wins() + j.draws() / 2.0) / j.played())).rjust(k.width)
                    elif k.columnType == "winPercentNFL":
                        rval += ("undef" if j.wins() + j.losses() == 0
                                 else "%.3f" % (j.wins() / (j.wins() + j.losses()))).rjust(k.width)
                    elif k.columnType == "winPercentPure":
                        rval += ("undef" if j.played() == 0
                                 else "%.3f" % (j.wins() / j.played())).rjust(k.width)
                    elif k.columnType == "resultsGrid":
                        gridLine = ""
                        for yIndex, y in enumerate(self.data):
                            for z in y:
                                if yIndex != 0:
                                    gridLine += "  "
                                result = j.result(z.name())
                                if result[0] >= 0:
                                    gridLine += qNumber(result[0]) + "–" + qNumber(result[1])
                                else:
                                    gridLine += " — "
                        rval += gridLine.rjust(k.width)
                rval += "\n"
                acc += 1
            rank = acc
        return rval

    def updateMatches(self):
        self.unsortedData = {}
        for i in self.matches:
            self.addMatchToData(i)
