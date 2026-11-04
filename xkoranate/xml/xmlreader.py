from ..uuids import parseUuid
from ..event import XkorEvent
from ..group import XkorGroup
from ..athlete import XkorAthlete
from ..rplist import XkorRPList
from ..signuplist import XkorSignupList
from ..variant import toDouble, toInt
from .xmlbasereader import XkorXmlBaseReader


class XkorXmlReader(XkorXmlBaseReader):
    def __init__(self, filename):
        super().__init__()
        self.m_rpList = None
        self.m_events = []  # list of (uuid.UUID, XkorEvent) pairs
        self.readDocument(filename, "scorinationFile", "This file is not an xkoranate version 0.3 file.")

    def events(self):
        return list(self.m_events)

    def readEvent(self):
        event = XkorEvent()
        id = parseUuid(self.attributes().value("id"))
        event.setName(self.attributes().value("name"))
        for name in self.childElements():
            if name == "sport":
                event.setSport(self.readString())
            elif name == "competition":
                event.setCompetition(self.readString())
            elif name == "paradigmOptions":
                event.setParadigmOptions(self.readOptions())
            elif name == "competitionOptions":
                event.setCompetitionOptions(self.readOptions())
            elif name == "results":
                event.setResults(self.readResults())
            elif name == "signupList":
                event.setSignupList(self.readEventSignupList())
            elif name == "group":
                event.addGroup(self.readGroup())
            else:
                self.readUnknownElement()
        self.m_events.append((id, event))

    def readEventSignupList(self):
        rval = XkorSignupList()

        for name in self.childElements():
            if name == "maxRank":
                rval.setMaxRank(self.readDouble())
            elif name == "minRank":
                rval.setMinRank(self.readDouble())
            elif name == "signup":
                rval.addAthlete(self.readSignup())
            else:
                self.readUnknownElement()
        return rval

    def readFile(self):
        for name in self.childElements():
            if name == "rpList":
                self.readRPList()
            elif name == "event":
                self.readEvent()
            else:
                self.readUnknownElement()

    def readGroup(self):
        rval = XkorGroup()
        rval.name = self.attributes().value("name")
        for name in self.childElements():
            if name == "signup":
                # C++: QList<QUuid>::append(QString) converts implicitly via QUuid(QString)
                rval.athletes.append(parseUuid(self.readString()))
            else:
                self.readUnknownElement()
        return rval

    def readNation(self):
        name = self.attributes().value("name")
        properties = {}

        for child in self.childElements():
            if child == "property":
                type = self.attributes().value("type")
                value = self.readDouble()
                properties[type] = value
            else:
                self.readUnknownElement()
        return (name, properties)

    def readResults(self):
        rval = {}
        for name in self.childElements():
            if name == "result":
                matchday = toInt(self.attributes().value("matchday"))
                rval[matchday] = self.readString()
            else:
                self.readUnknownElement()
        return rval

    def readRPList(self):
        self.m_rpList = XkorRPList()

        for name in self.childElements():
            if name == "competitionName":
                self.m_rpList.setCompetitionName(self.readString())
            elif name == "maxBonus":
                self.m_rpList.setMaxBonus(self.readDouble())
            elif name == "minBonus":
                self.m_rpList.setMinBonus(self.readDouble())
            elif name == "nation":
                self.m_rpList.addBonus(self.readNation())
            elif name == "rpCalculationType":
                self.m_rpList.setRPCalculationType(self.readString())
            elif name == "rpEffect":
                self.m_rpList.setRPEffect(self.readDouble())
            elif name == "rpOptions":
                self.m_rpList.setRPOptions(self.readOptions())
            elif name == "useTeams":
                self.m_rpList.setUseTeams(self.readString() != "false")
            else:
                self.readUnknownElement()

    def readSignup(self):
        ath = XkorAthlete()
        ath.id = parseUuid(self.attributes().value("id"))
        ath.name = self.attributes().value("name")
        ath.nation = self.attributes().value("nation")
        ath.skill = toDouble(self.attributes().value("skill"))
        # readOptions() leaves us on the signup's end element; the surrounding
        # loop advances from there. Reading ahead here swallowed whatever
        # followed, which is harmless whitespace in pretty-printed files but
        # eats the next <signup> when the file has no indentation.
        ath.properties = self.readOptions()
        return ath

    def rpList(self):
        return self.m_rpList
