from ..sport import XkorSport
from ..variant import toDouble
from .xmlbasereader import XkorXmlBaseReader


class XkorXmlSportReader(XkorXmlBaseReader):
    def __init__(self, filename):
        super().__init__()
        self.m_sport = XkorSport()
        self.m_filename = filename
        self.readDocument(self.m_filename, "sport", "The file ‘%s’ is not an xkoranate version 0.3 sport." % self.m_filename)

    def errorLocation(self):
        return " of ‘%s’" % self.m_filename

    def readDataPoints(self):
        rval = {}  # QMap<double, double>: iterate sorted(rval.items())

        for name in self.childElements():
            if name == "dataPoint":
                pos = toDouble(self.attributes().value("pos"))
                rval[pos] = self.readDouble()
            else:
                self.readUnknownElement()
        return rval

    def readFile(self):
        for name in self.childElements():
            if name == "name":
                self.m_sport.setName(self.readString())
            elif name == "alphabetizedName":
                self.m_sport.setAlphabetizedName(self.readString())
            elif name == "discipline":
                self.m_sport.setDiscipline(self.readString())
            elif name == "event":
                self.m_sport.setEvent(self.readString())
            elif name == "scorinator":
                self.m_sport.setScorinator(self.readString())
            elif name == "paradigm":
                self.m_sport.setParadigm(self.readString())
            elif name == "paradigmOptions":
                options = self.readOptions()
                self.m_sport.setParadigmOptions(options)
            elif name == "dataPoints":
                dataPointsName = self.attributes().value("name")
                dataPoints = self.readDataPoints()
                self.m_sport.addDataPoints(dataPointsName, dataPoints)
            else:
                self.readUnknownElement()

    def sport(self):
        return self.m_sport
