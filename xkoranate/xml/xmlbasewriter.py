from contextlib import contextmanager

from PySide6.QtCore import QFile, QIODevice, QXmlStreamWriter


class XkorXmlBaseWriter(QXmlStreamWriter):
    """Shared plumbing for the xkoranate version 0.3 XML writers."""

    @contextmanager
    def document(self, filename, rootName):
        """Write filename as a version 0.3 document; the body goes in the with block."""
        # stream writer settings
        self.setAutoFormatting(True)
        self.setAutoFormattingIndent(-1)

        f = QFile(filename)
        f.open(QIODevice.WriteOnly)

        self.setDevice(f)

        self.writeStartDocument()
        self.writeStartElement(rootName)
        self.writeAttribute("version", "0.3")
        yield
        self.writeEndDocument()

        f.close()

    def writeBoolElement(self, name, value):
        self.writeTextElement(name, "true" if value else "false")
