from ..variant import qNumber
from .xmlbasewriter import XkorXmlBaseWriter


class XkorXmlTableWriter(XkorXmlBaseWriter):
    def __init__(self, filename, t):
        super().__init__()
        with self.document(filename, "table"):
            self.writeTable(t)

    def writeTable(self, t):
        self.writeStartElement("sortCriteria")
        sortCriteria = t.getSortCriteria()
        for i in sortCriteria:
            self.writeTextElement("sortCriterion", i)
        self.writeEndElement()

        self.writeTextElement("pointsForWin", qNumber(t.getPointsForWin()))
        self.writeTextElement("pointsForDraw", qNumber(t.getPointsForDraw()))
        self.writeTextElement("pointsForLoss", qNumber(t.getPointsForLoss()))
        # only written when actually overridden — a table that leaves these
        # following pointsForWin/pointsForLoss must keep doing so after a
        # save/reload round trip, so writing the resolved value isn't an option
        for name, value in (("pointsForOTWin", t.getRawPointsForOTWin()),
                            ("pointsForSOWin", t.getRawPointsForSOWin()),
                            ("pointsForOTLoss", t.getRawPointsForOTLoss()),
                            ("pointsForSOLoss", t.getRawPointsForSOLoss())):
            if value is not None:
                self.writeTextElement(name, qNumber(value))

        self.writeTextElement("columnWidth", str(t.getColumnWidth()))
        self.writeBoolElement("showDraws", t.getShowDraws())
        self.writeBoolElement("showOvertime", t.getShowOvertime())
        self.writeBoolElement("showResultsGrid", t.getShowResultsGrid())
        self.writeTextElement("goalName", t.getGoalName())

        coinFlips = t.getCoinFlips()
        if coinFlips:
            # a "coin flip" tiebreaker's result is persisted once made, so
            # reopening this file (or just regenerating the table) doesn't
            # re-roll it — see XkorTableSorter's "coinFlip" sort criterion
            self.writeStartElement("coinFlips")
            for teamName in sorted(coinFlips):
                self.writeStartElement("coinFlip")
                self.writeAttribute("team", teamName)
                self.writeCharacters(qNumber(coinFlips[teamName]))
                self.writeEndElement()
            self.writeEndElement()

        self.writeStartElement("matches")
        matches = t.getMatches()
        for i in matches:
            decider = (" " + i.decider) if getattr(i, "decider", None) else ""
            self.writeTextElement("match", "%s %s–%s%s %s" % (i.team1, qNumber(i.score1), qNumber(i.score2), decider, i.team2))
        self.writeEndElement()
