import sys

from ..uuids import uuidToString
from ..variant import qNumber, toList, toString
from .xmlbasewriter import XkorXmlBaseWriter


class XkorXmlWriter(XkorXmlBaseWriter):
    def __init__(self, filename, rpList, events):
        super().__init__()
        with self.document(filename, "scorinationFile"):
            self.writeRPList(rpList)
            self.writeEvents(events)

    def writeEvents(self, events):
        for i in events:  # list of (uuid, XkorEvent) pairs
            id, event = i
            self.writeStartElement("event")
            self.writeAttribute("id", uuidToString(id))
            self.writeAttribute("name", event.name())
            self.writeTextElement("sport", event.sport())
            self.writeTextElement("competition", event.competition())

            self.writeOptions("paradigmOptions", event.paradigmOptions())
            self.writeOptions("competitionOptions", event.competitionOptions())

            self.writeStartElement("results")
            results = event.results()
            for matchday, result in results.items():
                self.writeStartElement("result")
                self.writeAttribute("matchday", str(matchday))
                self.writeCharacters(result)
                self.writeEndElement()
            self.writeEndElement()

            self.writeStartElement("signupList")
            signupList = event.signupList()
            self.writeTextElement("minRank", qNumber(signupList.minRank()))
            self.writeTextElement("maxRank", qNumber(signupList.maxRank()))

            athletes = signupList.athletes()
            for j in athletes:
                self.writeStartElement("signup")
                self.writeAttribute("id", uuidToString(j.id))
                self.writeAttribute("name", j.name)
                self.writeAttribute("nation", j.nation)
                self.writeAttribute("skill", qNumber(j.skill))

                signupProperties = j.properties
                for key, value in signupProperties.items():
                    self.writeVariant(value, key)
                self.writeEndElement()
            self.writeEndElement()

            groups = event.groups()
            for j in groups:
                self.writeStartElement("group")
                self.writeAttribute("name", j.name)
                for k in j.athletes:
                    self.writeTextElement("signup", uuidToString(k))
                self.writeEndElement()
            self.writeEndElement()

    def writeRPList(self, rpList):
        self.writeStartElement("rpList")
        self.writeBoolElement("useTeams", rpList.useTeams())
        self.writeTextElement("competitionName", rpList.competitionName())
        self.writeTextElement("rpEffect", qNumber(rpList.rpEffect()))
        self.writeTextElement("rpCalculationType", rpList.rpCalculationType())
        self.writeTextElement("minBonus", qNumber(rpList.minBonus()))
        self.writeTextElement("maxBonus", qNumber(rpList.maxBonus()))

        self.writeOptions("rpOptions", rpList.rpOptions())

        bonuses = rpList.bonuses()
        for nation, properties in bonuses.items():
            self.writeStartElement("nation")
            self.writeAttribute("name", nation)
            for type, value in properties.items():
                self.writeStartElement("property")
                self.writeAttribute("type", type)
                self.writeCharacters(qNumber(value))
                self.writeEndElement()
            self.writeEndElement()
        self.writeEndElement()

    def writeOptions(self, name, options):
        self.writeStartElement(name)
        for key, value in options.items():
            self.writeVariant(value, key)
        self.writeEndElement()

    def writeVariant(self, value, key=""):
        # NB: bool must be checked before int (Python bool is an int subclass);
        # C++ QVariant::Bool falls through to the unknown-type branch
        if isinstance(value, float):
            self.writeStartElement("double")
        elif isinstance(value, int) and not isinstance(value, bool):
            self.writeStartElement("int")
        elif isinstance(value, list):
            self.writeStartElement("list")
            if key != "":
                self.writeAttribute("type", key)
            list_ = toList(value)
            for i in list_:
                self.writeVariant(i)
            self.writeEndElement()
            return  # don’t run the code intended for basic types
        elif isinstance(value, str):
            self.writeStartElement("string")
        else:
            print("unknown QVariant type", type(value).__name__,
                  "encountered in XkorXmlWriter::writeVariant(QString, QVariant)", file=sys.stderr)
            return  # WTF?

        # remaining code is used for double, int, string
        if key != "":
            self.writeAttribute("type", key)
        self.writeCharacters(toString(value))
        self.writeEndElement()
