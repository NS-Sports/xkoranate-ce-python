from contextlib import contextmanager

from PySide6.QtCore import QIODevice, QSaveFile, QXmlStreamWriter


class XkorXmlBaseWriter(QXmlStreamWriter):
    """Shared plumbing for the xkoranate version 0.3 XML writers."""

    @contextmanager
    def document(self, filename, rootName):
        """Write filename as a version 0.3 document; the body goes in the with block.
        Raises OSError if the file can't be opened or written.

        The document goes to a temporary file that only replaces filename
        once all of it has been written. Opening filename itself emptied it
        before a byte was written, so a save that failed partway — a full
        disk, a writer that raised — left half a document where the last
        good save had been, and the user's retry had nothing to fall back on.
        """
        # stream writer settings
        self.setAutoFormatting(True)
        self.setAutoFormattingIndent(-1)

        f = QSaveFile(filename)
        # a folder that lets us rewrite the file but not create one beside it
        # (some network shares) can't hold the temporary copy; writing in
        # place there, as before, beats refusing to save at all
        f.setDirectWriteFallback(True)
        if not f.open(QIODevice.WriteOnly):
            raise OSError("Could not save ‘%s’: %s" % (filename, f.errorString()))

        self.setDevice(f)
        try:
            self.writeStartDocument()
            self.writeStartElement(rootName)
            self.writeAttribute("version", "0.3")
            yield
            self.writeEndDocument()
        except BaseException:
            f.cancelWriting()  # commit() then throws the temporary file away
            f.commit()
            raise
        finally:
            self.setDevice(None)

        if self.hasError():
            f.cancelWriting()
        error = f.errorString()
        if not f.commit():
            raise OSError("Could not save ‘%s’: %s" % (filename, f.errorString() or error))

    def writeBoolElement(self, name, value):
        self.writeTextElement(name, "true" if value else "false")
