import sys

from PySide6.QtCore import QFile, QIODevice, QXmlStreamReader

from ..variant import toDouble, toInt


class XkorXmlBaseReader(QXmlStreamReader):
    """Shared plumbing for the xkoranate version 0.3 XML readers.

    Subclasses set up their state, then call readDocument(); readFile()
    reads the children of the root element.
    """

    def readDocument(self, filename, rootName, badRootMessage):
        f = QFile(filename)
        if not f.exists():
            cls = type(self).__name__
            self.raiseError("File ‘%s’ not found by %s::%s(QString)" % (filename, cls, cls))
            return
        if not f.open(QIODevice.ReadOnly):
            self.raiseError("Could not open ‘%s’: %s" % (filename, f.errorString()))
            return
        self.setDevice(f)

        while not self.atEnd():
            if self.isStartElement():
                if self.name() == rootName and self.attributes().value("version") == "0.3":
                    self.readFile()
                else:
                    self.raiseError(badRootMessage)
            self.readNext()

        if self.hasError():
            print(self.error(), file=sys.stderr)

        f.close()

    def errorLocation(self):
        """Text placed after the line/column in error()."""
        return ""

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
        rval += "\nError occured at line %s, column %s%s." % (str(self.lineNumber()), str(self.columnNumber()), self.errorLocation())
        return rval

    def childElements(self):
        """Yield the name of each child element of the current element.

        The loop body must consume the child (read it or skip it).
        """
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break
            if self.isStartElement():
                yield self.name()

    def readValues(self):
        """Yield (type attribute, value) for each typed child element."""
        for name in self.childElements():
            type = self.attributes().value("type")
            if name == "double":
                value = self.readDouble()
            elif name == "int":
                value = self.readInt()
            elif name == "list":
                value = self.readList()
            elif name == "string":
                value = self.readString()
            else:
                self.readUnknownElement()
                continue
            yield type, value

    def readDouble(self):
        return toDouble(self.readElementText())

    def readInt(self):
        return toInt(self.readElementText())

    def readList(self):
        return [value for _type, value in self.readValues()]

    def readOptions(self):
        return dict(self.readValues())

    def readString(self):
        return self.readElementText()

    def readUnknownElement(self):
        for _name in self.childElements():
            self.readUnknownElement()
