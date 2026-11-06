"""Saving from the scorinator and the table generator: Save on an untitled
file has to wait for Save As, and a save that doesn't happen (cancelled, or
the file couldn't be written) must never let unsaved work be dropped."""

import os
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from xkoranate.rplist import XkorRPList
from xkoranate.tablegenerator.table import XkorTable
from xkoranate.xml.xmlreader import XkorXmlReader
from xkoranate.xml.xmltablereader import XkorXmlTableReader
from xkoranate.xml.xmltablewriter import XkorXmlTableWriter
from xkoranate.xml.xmlwriter import XkorXmlWriter


def _central():
    from xkoranate.centralwidget import XkorCentralWidget
    w = XkorCentralWidget()
    return SimpleNamespace(widget=w, edit=w.setModified, startOver=w.newFile,
                           isModified=lambda: w.modified)


def _generator():
    from xkoranate.tablegenerator.tablegenerator import XkorTableGenerator
    w = XkorTableGenerator()
    return SimpleNamespace(widget=w, edit=w.setFileModified, startOver=w.reset,
                           isModified=lambda: w.fileModified)


both_widgets = pytest.mark.parametrize(
    "make", [_central, _generator], ids=["scorinator", "table generator"])


@pytest.fixture
def edited(qapp, monkeypatch):
    """edited(make) -> an untitled widget with unsaved changes, whose
    unsaved-changes prompt answers Save. Its renamed list collects every
    fileChanged it emits."""
    def build(make):
        s = make()
        s.edit()
        s.renamed = []
        s.widget.fileChanged.connect(s.renamed.append)
        monkeypatch.setattr(s.widget, "showUnsavedDialog", lambda: QMessageBox.Save)
        return s
    return build


def _answer_save_as(s, monkeypatch, filename):
    """Have the widget's Save As dialog choose filename ("" for Cancel)
    without showing it."""
    monkeypatch.setattr(s.widget.dialog, "exec",
                        lambda: QDialog.Accepted if filename else QDialog.Rejected)
    monkeypatch.setattr(s.widget.dialog, "selectedFiles",
                        lambda: [filename] if filename else [])


@pytest.fixture
def errors(monkeypatch):
    """The text of every error box shown, without showing it."""
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: shown.append(text))
    return shown


@both_widgets
def test_cancelling_save_as_keeps_the_unsaved_work(make, edited, monkeypatch):
    s = edited(make)
    _answer_save_as(s, monkeypatch, "")

    assert s.widget.saveFile() is False
    assert s.widget.okayToLoad() is False
    s.startOver()
    assert not s.widget.close()

    assert s.isModified()
    assert s.widget.currentFileName == ""
    assert s.renamed == []


@both_widgets
def test_choosing_a_file_in_save_as_saves_before_starting_over(make, edited, monkeypatch, tmp_path):
    path = str(tmp_path / "saved.xml")
    s = edited(make)
    _answer_save_as(s, monkeypatch, path)

    assert s.widget.okayToLoad() is True

    assert os.path.exists(path)
    assert not s.isModified()
    assert s.widget.currentFileName == path
    assert s.renamed == [path]


@both_widgets
def test_a_save_that_cannot_be_written_keeps_the_unsaved_work(make, edited, errors, monkeypatch, tmp_path):
    path = str(tmp_path / "missing folder" / "saved.xml")
    s = edited(make)
    _answer_save_as(s, monkeypatch, path)

    assert s.widget.okayToLoad() is False

    assert len(errors) == 1 and "saved.xml" in errors[0]
    assert s.isModified()
    assert s.widget.currentFileName == ""
    assert s.renamed == []


def test_the_writers_raise_when_the_file_cannot_be_opened(tmp_path):
    path = str(tmp_path / "missing folder" / "saved.xml")
    with pytest.raises(OSError, match="saved.xml"):
        XkorXmlWriter(path, XkorRPList(), [])
    with pytest.raises(OSError, match="saved.xml"):
        XkorXmlTableWriter(path, XkorTable())


@pytest.mark.parametrize("error", [OSError("No space left on device"), RuntimeError("a writer bug")])
@pytest.mark.parametrize("writer, method, write", [
    (XkorXmlWriter, "writeEvents", lambda path: XkorXmlWriter(path, XkorRPList(), [])),
    (XkorXmlTableWriter, "writeTable", lambda path: XkorXmlTableWriter(path, XkorTable())),
], ids=["scorinator", "table generator"])
def test_a_failed_save_leaves_the_previous_file_intact(writer, method, write, error, tmp_path,
                                                       monkeypatch):
    """Opening the file to write it used to empty it first, so a save that
    failed partway left half a document where the last good one had been."""
    path = str(tmp_path / "saved.xml")
    write(path)
    with open(path, encoding="utf-8") as f:
        before = f.read()

    def fail(self, *args):
        self.writeTextElement("halfway", "through")
        raise error

    monkeypatch.setattr(writer, method, fail)
    with pytest.raises(type(error)):
        write(path)

    with open(path, encoding="utf-8") as f:
        assert f.read() == before
    assert os.listdir(str(tmp_path)) == ["saved.xml"]  # no temporary file left behind


@pytest.mark.parametrize("reader", [XkorXmlReader, XkorXmlTableReader])
def test_the_readers_report_a_file_they_cannot_open(reader, tmp_path):
    r = reader(str(tmp_path))  # exists, but a folder can't be opened as a file
    assert r.hasError()
    assert str(tmp_path) in r.error()
