import sys

from PySide6.QtCore import QFile, QIODevice, QXmlStreamReader

from ..uuids import parseUuid
from ..event import XkorEvent
from ..group import XkorGroup
from ..athlete import XkorAthlete
from ..rplist import XkorRPList
from ..signuplist import XkorSignupList
from ..variant import toDouble, toInt


class XkorXmlReader(QXmlStreamReader):
    def __init__(self, filename):
        super().__init__()
        self.m_rpList = None
        self.m_events = []  # list of (uuid.UUID, XkorEvent) pairs

        f = QFile(filename)
        if not f.exists():
            self.raiseError("File ‘%s’ not found by XkorXmlReader::XkorXmlReader(QString)" % filename)
            return
        f.open(QIODevice.ReadOnly)
        self.setDevice(f)

        while not self.atEnd():
            if self.isStartElement():
                if self.name() == "scorinationFile" and self.attributes().value("version") == "0.3":
                    self.readFile()
                else:
                    self.raiseError("This file is not an xkoranate version 0.3 file.")
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

    def events(self):
        return list(self.m_events)

    def readDouble(self):
        return toDouble(self.readElementText())

    def readEvent(self):
        event = XkorEvent()
        id = parseUuid(self.attributes().value("id"))
        event.setName(self.attributes().value("name"))
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "sport":
                    event.setSport(self.readString())
                elif self.name() == "competition":
                    event.setCompetition(self.readString())
                elif self.name() == "paradigmOptions":
                    event.setParadigmOptions(self.readOptions())
                elif self.name() == "competitionOptions":
                    event.setCompetitionOptions(self.readOptions())
                elif self.name() == "results":
                    event.setResults(self.readResults())
                elif self.name() == "signupList":
                    event.setSignupList(self.readEventSignupList())
                elif self.name() == "group":
                    event.addGroup(self.readGroup())
                else:
                    self.readUnknownElement()
        self.m_events.append((id, event))

    def readEventSignupList(self):
        rval = XkorSignupList()

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "maxRank":
                    rval.setMaxRank(self.readDouble())
                elif self.name() == "minRank":
                    rval.setMinRank(self.readDouble())
                elif self.name() == "signup":
                    rval.addAthlete(self.readSignup())
                else:
                    self.readUnknownElement()
        return rval

    def readFile(self):
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "rpList":
                    self.readRPList()
                elif self.name() == "event":
                    self.readEvent()
                else:
                    self.readUnknownElement()

    def readGroup(self):
        rval = XkorGroup()
        rval.name = self.attributes().value("name")
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "signup":
                    # C++: QList<QUuid>::append(QString) converts implicitly via QUuid(QString)
                    rval.athletes.append(parseUuid(self.readString()))
                else:
                    self.readUnknownElement()
        return rval

    def readInt(self):
        return toInt(self.readElementText())

    def readList(self):
        rval = []
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "double":
                    value = self.readDouble()
                    rval.append(value)
                elif self.name() == "int":
                    value = self.readInt()
                    rval.append(value)
                elif self.name() == "list":
                    value = self.readList()
                    rval.append(value)
                elif self.name() == "string":
                    value = self.readString()
                    rval.append(value)
                else:
                    self.readUnknownElement()
        # self.readNext()  # skip end element
        return rval

    def readNation(self):
        name = self.attributes().value("name")
        properties = {}

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "property":
                    type = self.attributes().value("type")
                    value = self.readDouble()
                    properties[type] = value
                else:
                    self.readUnknownElement()
        return (name, properties)

    def readOptions(self):
        rval = {}
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                type = self.attributes().value("type")
                if self.name() == "double":
                    value = self.readDouble()
                    rval[type] = value
                elif self.name() == "int":
                    value = self.readInt()
                    rval[type] = value
                elif self.name() == "list":
                    value = self.readList()
                    rval[type] = value
                elif self.name() == "string":
                    value = self.readString()
                    rval[type] = value
                else:
                    self.readUnknownElement()
        return rval

    def readResults(self):
        rval = {}
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "result":
                    matchday = toInt(self.attributes().value("matchday"))
                    rval[matchday] = self.readString()
                else:
                    self.readUnknownElement()
        return rval

    def readRPList(self):
        self.m_rpList = XkorRPList()

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                if self.name() == "competitionName":
                    self.m_rpList.setCompetitionName(self.readString())
                elif self.name() == "maxBonus":
                    self.m_rpList.setMaxBonus(self.readDouble())
                elif self.name() == "minBonus":
                    self.m_rpList.setMinBonus(self.readDouble())
                elif self.name() == "nation":
                    self.m_rpList.addBonus(self.readNation())
                elif self.name() == "rpCalculationType":
                    self.m_rpList.setRPCalculationType(self.readString())
                elif self.name() == "rpEffect":
                    self.m_rpList.setRPEffect(self.readDouble())
                elif self.name() == "rpOptions":
                    self.m_rpList.setRPOptions(self.readOptions())
                elif self.name() == "useTeams":
                    self.m_rpList.setUseTeams(self.readString() != "false")
                else:
                    self.readUnknownElement()

    def readSignup(self):
        ath = XkorAthlete()
        ath.id = parseUuid(self.attributes().value("id"))
        ath.name = self.attributes().value("name")
        ath.nation = self.attributes().value("nation")
        ath.skill = toDouble(self.attributes().value("skill"))
        ath.properties = self.readOptions()

        self.readNext()
        return ath

    def readString(self):
        return self.readElementText()

    def readUnknownElement(self):
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                self.readUnknownElement()

    def rpList(self):
        return self.m_rpList
