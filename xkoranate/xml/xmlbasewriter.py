from contextlib import contextmanager

from PySide6.QtCore import QBuffer, QIODevice, QSaveFile, QXmlStreamWriter


class XkorXmlBaseWriter(QXmlStreamWriter):
    """Shared plumbing for the xkoranate version 0.3 XML writers."""

    @contextmanager
    def document(self, filename, rootName):
        """Write filename as a version 0.3 document; the body goes in the with block.
        Raises OSError if the file can't be opened or written.

        The document is built in memory and only then saved through a
        temporary file that replaces filename once complete, so a failed
        save leaves the last good one in place. A folder that won't take a
        temporary file (some network shares) gets filename rewritten in place.
        """
        # stream writer settings
        self.setAutoFormatting(True)
        self.setAutoFormattingIndent(-1)

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        self.setDevice(buffer)
        try:
            self.writeStartDocument()
            self.writeStartElement(rootName)
            self.writeAttribute("version", "0.3")
            yield
            self.writeEndDocument()
        finally:
            self.setDevice(None)
            buffer.close()
        if self.hasError():
            raise OSError("Could not save ‘%s’: the document could not be written" % filename)

        f = QSaveFile(filename)
        f.setDirectWriteFallback(True)
        if not f.open(QIODevice.WriteOnly):
            raise OSError("Could not save ‘%s’: %s" % (filename, f.errorString()))
        if f.write(buffer.data()) != buffer.size():
            # read before cancelWriting() replaces it with "Writing canceled"
            error = f.errorString()
            f.cancelWriting()
            f.commit()  # throws the temporary file away
            raise OSError("Could not save ‘%s’: %s" % (filename, error))
        if not f.commit():
            raise OSError("Could not save ‘%s’: %s" % (filename, f.errorString()))

    def writeBoolElement(self, name, value):
        self.writeTextElement(name, "true" if value else "false")
