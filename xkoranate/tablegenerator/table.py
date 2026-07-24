from ..variant import qNumber
from .tablematch import XkorTableMatch
from .tablerow import XkorTableRow
from .tablesorter import XkorTableSorter


class XkorTable:
    def __init__(self):
        self.tableName = ""
        self.columns = []
        self.matches = []
        self.unsortedData = {}  # QHash<QString, XkorTableRow>
        self.data = []
        self.sortCriteria = []
        self.sorter = XkorTableSorter()
        self.pointsForWin = 0.0
        self.pointsForDraw = 0.0
        self.pointsForLoss = 0.0
        # None means "not overridden": fall back to pointsForWin/pointsForLoss
        # so tables that never use OT/SO deciders score exactly as before
        self.pointsForOTWin = None
        self.pointsForSOWin = None
        self.pointsForOTLoss = None
        self.pointsForSOLoss = None
        self.columnWidth = 0
        self.showDraws = False
        self.showResultsGrid = False
        self.showOvertime = False
        self.goalName = ""

    def addMatchToData(self, m):
        i = self.findTeam(m.team1)
        i.insertMatch(m.team2, m.score1, m.score2, True, m.decider)
        i = self.findTeam(m.team2)
        i.insertMatch(m.team1, m.score2, m.score1, False, m.decider)

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

        oldData = []
        for i in self.unsortedData.values():
            oldData.append(i.clone())

        self.collapse(self.data, self.sortTable(oldData))

    def getPoints(self, a):
        return (a.regulationWins() * self.pointsForWin
                + a.draws() * self.pointsForDraw
                + a.regulationLosses() * self.pointsForLoss
                + a.otWins() * self.getPointsForOTWin()
                + a.soWins() * self.getPointsForSOWin()
                + a.otLosses() * self.getPointsForOTLoss()
                + a.soLosses() * self.getPointsForSOLoss())

    def getColumns(self):
        return list(self.columns)

    def getMatches(self):
        return list(self.matches)

    def getColumnWidth(self):
        return self.columnWidth

    def getGoalName(self):
        return self.goalName

    def getPointsForWin(self):
        return self.pointsForWin

    def getPointsForDraw(self):
        return self.pointsForDraw

    def getPointsForLoss(self):
        return self.pointsForLoss

    def getPointsForOTWin(self):
        return self.pointsForOTWin if self.pointsForOTWin is not None else self.pointsForWin

    def getPointsForSOWin(self):
        return self.pointsForSOWin if self.pointsForSOWin is not None else self.pointsForWin

    def getPointsForOTLoss(self):
        return self.pointsForOTLoss if self.pointsForOTLoss is not None else self.pointsForLoss

    def getPointsForSOLoss(self):
        return self.pointsForSOLoss if self.pointsForSOLoss is not None else self.pointsForLoss

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

    def setColumns(self, c):
        self.columns = list(c)

    def setColumnWidth(self, width):
        self.columnWidth = width

    def setGoalName(self, name):
        self.goalName = name

    def setMatches(self, m):
        self.matches = list(m)
        self.updateMatches()

    def setPointsForWin(self, pts):
        self.pointsForWin = pts
        self.sorter.setPointsForWin(pts)

    def setPointsForDraw(self, pts):
        self.pointsForDraw = pts
        self.sorter.setPointsForDraw(pts)

    def setPointsForLoss(self, pts):
        self.pointsForLoss = pts
        self.sorter.setPointsForLoss(pts)

    def setPointsForOTWin(self, pts):
        self.pointsForOTWin = pts
        self.sorter.setPointsForOTWin(pts)

    def setPointsForSOWin(self, pts):
        self.pointsForSOWin = pts
        self.sorter.setPointsForSOWin(pts)

    def setPointsForOTLoss(self, pts):
        self.pointsForOTLoss = pts
        self.sorter.setPointsForOTLoss(pts)

    def setPointsForSOLoss(self, pts):
        self.pointsForSOLoss = pts
        self.sorter.setPointsForSOLoss(pts)

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
                    elif k.columnType == "played":
                        rval += qNumber(j.played()).rjust(k.width)
                    elif k.columnType == "wins":
                        rval += qNumber(j.wins()).rjust(k.width)
                    elif k.columnType == "draws":
                        rval += qNumber(j.draws()).rjust(k.width)
                    elif k.columnType == "losses":
                        rval += qNumber(j.losses()).rjust(k.width)
                    elif k.columnType == "otWins":
                        rval += qNumber(j.otWins()).rjust(k.width)
                    elif k.columnType == "soWins":
                        rval += qNumber(j.soWins()).rjust(k.width)
                    elif k.columnType == "otLosses":
                        rval += qNumber(j.otLosses()).rjust(k.width)
                    elif k.columnType == "soLosses":
                        rval += qNumber(j.soLosses()).rjust(k.width)
                    elif k.columnType == "goalsFor":
                        rval += qNumber(j.goalsFor()).rjust(k.width)
                    elif k.columnType == "goalsAgainst":
                        rval += qNumber(j.goalsAgainst()).rjust(k.width)
                    elif k.columnType == "goalDifference":
                        rval += (("+" if j.goalDifference() > 0
                                  else ("−" if j.goalDifference() < 0 else ""))
                                 + str(abs(int(j.goalDifference())))).rjust(k.width)
                    elif k.columnType == "goalAverage":
                        rval += ("∞" if j.goalsAgainst() == 0
                                 else "%.3f" % (j.goalsFor() / j.goalsAgainst())).rjust(k.width)
                    elif k.columnType == "points":
                        rval += qNumber(self.getPoints(j)).rjust(k.width)
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
