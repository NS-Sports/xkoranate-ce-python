from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QGridLayout, QMessageBox, QStackedWidget, QWidget

from .event import XkorEvent
from .eventeditor.eventeditor import XkorEventEditor
from .navigationwidget import XkorNavigationWidget
from .rpeditor.rpeditor import XkorRPEditor
from .rplist import XkorRPList
from .thinsplitter import XkorThinSplitter
from .ui.dialogs import (ask_file_name, ask_save_changes, open_file_dialog, parent_folder,
                         resolved_search_path)


class XkorCentralWidget(QWidget):
    eventDirectoryChanged = Signal(str)
    fileChanged = Signal(str)
    fileEdited = Signal()
    resultExportDirectoryChanged = Signal(str)
    signupListDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.currentEvent = None
        self.currentFileName = ""
        self.modified = False

        self.dialog = QFileDialog(self, "Save scorinator file", resolved_search_path("events"), "XML files (*.xml)")
        self.dialog.setDefaultSuffix("xml")
        self.dialog.setWindowModality(Qt.WindowModal)

        self.nw = XkorNavigationWidget()
        self.editor = QStackedWidget()

        # set up editor widgets
        self.rpe = XkorRPEditor()
        self.rpe.setData(self.nw.rpList())
        self.rpe.dataChanged.connect(self.setModified)
        self.editor.addWidget(self.rpe)
        self.editor.setCurrentWidget(self.rpe)
        self.nw.listChanged.connect(self.setModified)
        self.nw.editRPList.connect(self.rpe.setData)
        self.nw.editRPList.connect(self.showRPEditor)

        self.ee = XkorEventEditor()
        self.ee.dataChanged.connect(self.setModified)
        self.ee.resultExportDirectoryChanged.connect(self.resultExportDirectoryChanged)
        self.ee.signupListDirectoryChanged.connect(self.signupListDirectoryChanged)
        self.editor.addWidget(self.ee)
        self.nw.editEvent.connect(self.showEventEditor)

        splitter = XkorThinSplitter()
        splitter.addWidget(self.nw)
        splitter.addWidget(self.editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1093)  # only the main screen should stretch

        layout = QGridLayout(self)
        layout.addWidget(splitter)
        layout.setContentsMargins(0, 0, 0, 0)

    def closeEvent(self, event):
        if self.okayToLoad():
            QWidget.closeEvent(self, event)
        else:
            event.ignore()

    def events(self):
        self.updateCurrentEvent()
        return self.nw.events()

    def loadSports(self):
        self.ee.loadSports()

    def newFile(self):
        if self.okayToLoad():
            rpl = XkorRPList()
            events = []

            self.rpe.setData(rpl)
            self.ee.setData(XkorEvent(), XkorRPList())
            self.nw.reset()
            self.currentEvent = None

            self.nw.setRPList(rpl)
            self.nw.setEvents(events)

            self.editor.setCurrentWidget(self.rpe)

            self.currentFileName = ""
            self.fileChanged.emit(self.currentFileName)
            self.setModified(False)

    def okayToLoad(self):
        """Whether the current file may be replaced: it's unmodified, or the
        user discarded the changes, or saved them. A cancelled or failed
        save counts as Cancel."""
        if self.modified:
            result = self.showUnsavedDialog()
            if result == QMessageBox.Save:
                return self.saveFile()
            elif result == QMessageBox.Cancel:
                return False
        return True

    def openFile(self, filename=None):
        # C++ overloads: openFile() shows the dialog; openFile(QString) loads
        if filename is None:
            if self.okayToLoad():
                self.dialog.setAcceptMode(QFileDialog.AcceptOpen)
                self.dialog.setDirectory(resolved_search_path("events"))
                open_file_dialog(self.dialog, self.openFile)
            return

        if filename != "":
            from .xml.xmlreader import XkorXmlReader

            r = XkorXmlReader(filename)
            if r.hasError():
                QMessageBox.critical(self, "xkoranate", r.error())
            else:
                rpl = r.rpList()
                events = r.events()

                # wipe the slate clean
                self.rpe.setData(None)
                self.ee.setData(XkorEvent(), XkorRPList())
                self.nw.reset()
                self.currentEvent = None

                # load the new data
                self.nw.setRPList(rpl)
                self.nw.setEvents(events)

                # editor->setCurrentWidget(rpe); // show the default screen, which is the RP editor

                self.currentFileName = filename

                self.fileChanged.emit(filename)
                self.setModified(False)

                self.eventDirectoryChanged.emit(parent_folder(filename))

    def rpList(self):
        self.rpe.updateData()
        return self.nw.rpList()

    def saveFile(self, filename=""):
        """Save to filename, else to the current file, else ask where.
        Returns whether the file was saved."""
        if filename == "":  # if no filename was specified
            if self.currentFileName == "":  # still “Untitled”?
                return self.saveFileAs()
            filename = self.currentFileName

        from .xml.xmlwriter import XkorXmlWriter

        try:
            XkorXmlWriter(filename, self.rpList(), self.events())
        except OSError as e:
            QMessageBox.critical(self, "xkoranate", str(e))
            return False

        self.currentFileName = filename
        self.fileChanged.emit(filename)
        self.setModified(False)

        self.eventDirectoryChanged.emit(parent_folder(filename))
        return True

    def saveFileAs(self):
        """Ask where to save, then save there. Returns whether the file was
        saved: False if the user cancelled."""
        self.dialog.setAcceptMode(QFileDialog.AcceptSave)
        self.dialog.setDirectory(resolved_search_path("events"))
        filename = ask_file_name(self.dialog)
        return bool(filename) and self.saveFile(filename)

    def setModified(self, isModified=True):
        self.modified = isModified
        if isModified:
            self.fileEdited.emit()

    def showEventEditor(self, e):
        self.updateCurrentEvent()
        self.currentEvent = e
        self.ee.setData(e, self.rpList())
        self.editor.setCurrentWidget(self.ee)

    def showRPEditor(self):
        self.editor.setCurrentWidget(self.rpe)

    def showUnsavedDialog(self):
        return ask_save_changes(self, self.currentFileName)

    def updateCurrentEvent(self):
        if self.currentEvent is not None:
            # *currentEvent = ee->data(): copy the value into the existing object
            self.currentEvent.assignFrom(self.ee.data())  # data() returns a fresh copy
