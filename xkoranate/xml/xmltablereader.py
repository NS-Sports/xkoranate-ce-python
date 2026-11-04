from .xmlbasereader import XkorXmlBaseReader


class XkorXmlTableReader(XkorXmlBaseReader):
    def __init__(self, filename):
        super().__init__()
        from ..tablegenerator.table import XkorTable
        self.m_table = XkorTable()
        self.m_matches = ""
        self.readDocument(filename, "table", "This file is not an xkoranate version 0.3 table.")

    def matches(self):
        return self.m_matches

    def readFile(self):
        for name in self.childElements():
            if name == "sortCriteria":
                self.m_table.setSortCriteria(self.readSortCriteria())
            elif name == "pointsForWin":
                self.m_table.setPointsForWin(self.readDouble())
            elif name == "pointsForDraw":
                self.m_table.setPointsForDraw(self.readDouble())
            elif name == "pointsForLoss":
                self.m_table.setPointsForLoss(self.readDouble())
            elif name == "pointsForOTWin":
                self.m_table.setPointsForOTWin(self.readDouble())
            elif name == "pointsForSOWin":
                self.m_table.setPointsForSOWin(self.readDouble())
            elif name == "pointsForOTLoss":
                self.m_table.setPointsForOTLoss(self.readDouble())
            elif name == "pointsForSOLoss":
                self.m_table.setPointsForSOLoss(self.readDouble())
            elif name == "columnWidth":
                self.m_table.setColumnWidth(self.readInt())
            elif name == "goalName":
                self.m_table.setGoalName(self.readString())
            elif name == "showDraws":
                self.m_table.setShowDraws(self.readString() == "true")
            elif name == "showOvertime":
                self.m_table.setShowOvertime(self.readString() == "true")
            elif name == "showResultsGrid":
                self.m_table.setShowResultsGrid(self.readString() == "true")
            elif name == "matches":
                self.readMatches()
            elif name == "coinFlips":
                self.m_table.setCoinFlips(self.readCoinFlips())
            else:
                self.readUnknownElement()

    def readCoinFlips(self):
        rval = {}
        for name in self.childElements():
            if name == "coinFlip":
                teamName = str(self.attributes().value("team"))
                rval[teamName] = self.readDouble()
            else:
                self.readUnknownElement()
        return rval

    def readMatches(self):
        from ..tablegenerator.decider import parseMatchLine
        from ..tablegenerator.tablematch import XkorTableMatch

        matchesList = []

        for name in self.childElements():
            if name == "match":
                matchText = self.readString()

                parsed = parseMatchLine(matchText)
                if parsed is not None:  # if we matched
                    matchesList.append(XkorTableMatch(*parsed))
                self.m_matches += matchText + "\n"
            else:
                self.readUnknownElement()

        self.m_table.setMatches(matchesList)

    def readSortCriteria(self):
        rval = []

        for name in self.childElements():
            if name == "sortCriterion":
                rval.append(self.readString())
            else:
                self.readUnknownElement()

        return rval

    def table(self):
        # C++ returns m_table by value; the reader is transient so sharing is safe
        return self.m_table
