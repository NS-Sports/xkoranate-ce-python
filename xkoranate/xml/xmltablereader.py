import sys

from PySide6.QtCore import QFile, QIODevice, QXmlStreamReader

from ..variant import toDouble, toInt


class XkorXmlTableReader(QXmlStreamReader):
    def __init__(self, filename):
        super().__init__()
        from ..tablegenerator.table import XkorTable
        self.m_table = XkorTable()
        self.m_matches = ""

        f = QFile(filename)
        if not f.exists():
            self.raiseError("File ‘%s’ not found by XkorXmlTableReader::XkorXmlTableReader(QString)" % filename)
            return
        f.open(QIODevice.ReadOnly)
        self.setDevice(f)

        while not self.atEnd():
            if self.isStartElement():
                if self.name() == "table" and self.attributes().value("version") == "0.3":
                    self.readFile()
                else:
                    self.raiseError("This file is not an xkoranate version 0.3 table.")
            self.readNext()

        if self.hasError():
            print(self.error(), file=sys.stderr)

        f.close()

    def error(self):
        err = QXmlStreamReader.error(self)
        if err == QXmlStreamReader.Error.NoError:
            return ""  # no error
        elif err == QXmlStreamReader.Error.UnexpectedElementError:
            rval = "An unexpected element was found."
        elif err == QXmlStreamReader.Error.NotWellFormedError:
            rval = "The input file was not well-formed XML."
        elif err == QXmlStreamReader.Error.PrematureEndOfDocumentError:
            rval = "The document ended unexpectedly."
        else:  # CustomError
            rval = self.errorString()
        rval += "\nError occured at line %s, column %s." % (str(self.lineNumber()), str(self.columnNumber()))
        return rval

    def matches(self):
        return self.m_matches

    def readDouble(self):
        return toDouble(self.readElementText())

    def readFile(self):
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "sortCriteria":
                    self.m_table.setSortCriteria(self.readSortCriteria())
                elif self.name() == "pointsForWin":
                    self.m_table.setPointsForWin(self.readDouble())
                elif self.name() == "pointsForDraw":
                    self.m_table.setPointsForDraw(self.readDouble())
                elif self.name() == "pointsForLoss":
                    self.m_table.setPointsForLoss(self.readDouble())
                elif self.name() == "pointsForOTWin":
                    self.m_table.setPointsForOTWin(self.readDouble())
                elif self.name() == "pointsForSOWin":
                    self.m_table.setPointsForSOWin(self.readDouble())
                elif self.name() == "pointsForOTLoss":
                    self.m_table.setPointsForOTLoss(self.readDouble())
                elif self.name() == "pointsForSOLoss":
                    self.m_table.setPointsForSOLoss(self.readDouble())
                elif self.name() == "columnWidth":
                    self.m_table.setColumnWidth(self.readInt())
                elif self.name() == "goalName":
                    self.m_table.setGoalName(self.readString())
                elif self.name() == "showDraws":
                    self.m_table.setShowDraws(self.readString() == "true")
                elif self.name() == "showOvertime":
                    self.m_table.setShowOvertime(self.readString() == "true")
                elif self.name() == "showResultsGrid":
                    self.m_table.setShowResultsGrid(self.readString() == "true")
                elif self.name() == "matches":
                    self.readMatches()
                elif self.name() == "coinFlips":
                    self.m_table.setCoinFlips(self.readCoinFlips())
                else:
                    self.readUnknownElement()

    def readCoinFlips(self):
        rval = {}
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "coinFlip":
                    teamName = str(self.attributes().value("team"))
                    rval[teamName] = self.readDouble()
                else:
                    self.readUnknownElement()
        return rval

    def readInt(self):
        return toInt(self.readElementText())

    def readMatches(self):
        from ..tablegenerator.decider import parseMatchLine
        from ..tablegenerator.tablematch import XkorTableMatch

        matchesList = []

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "match":
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

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "sortCriterion":
                    rval.append(self.readString())
                else:
                    self.readUnknownElement()

        return rval

    def readString(self):
        return self.readElementText()

    def readUnknownElement(self):
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                self.readUnknownElement()

    def table(self):
        # C++ returns m_table by value; the reader is transient so sharing is safe
        return self.m_table
