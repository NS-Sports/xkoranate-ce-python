from contextlib import contextmanager

from PySide6.QtCore import QFile, QIODevice, QXmlStreamWriter


class XkorXmlBaseWriter(QXmlStreamWriter):
    """Shared plumbing for the xkoranate version 0.3 XML writers."""

    @contextmanager
    def document(self, filename, rootName):
        """Write filename as a version 0.3 document; the body goes in the with block.
        Raises OSError if the file can't be opened or written."""
        # stream writer settings
        self.setAutoFormatting(True)
        self.setAutoFormattingIndent(-1)

        f = QFile(filename)
        if not f.open(QIODevice.WriteOnly):
            raise OSError("Could not save ‘%s’: %s" % (filename, f.errorString()))

        self.setDevice(f)

        self.writeStartDocument()
        self.writeStartElement(rootName)
        self.writeAttribute("version", "0.3")
        yield
        self.writeEndDocument()

        written = f.flush() and not self.hasError()
        error = f.errorString()
        f.close()
        if not written:
            raise OSError("Could not save ‘%s’: %s" % (filename, error))

    def writeBoolElement(self, name, value):
        self.writeTextElement(name, "true" if value else "false")
