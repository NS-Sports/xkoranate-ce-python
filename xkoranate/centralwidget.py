from PySide6.QtCore import QDir, QFileInfo, Qt, Signal
from PySide6.QtWidgets import QFileDialog, QGridLayout, QMessageBox, QStackedWidget, QWidget

from .event import XkorEvent
from .eventeditor.eventeditor import XkorEventEditor
from .navigationwidget import XkorNavigationWidget
from .rpeditor.rpeditor import XkorRPEditor
from .rplist import XkorRPList
from .thinsplitter import XkorThinSplitter
from .ui.dialogs import message_box, resolved_search_path


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
        self._dialogSlot = None  # bookkeeping for QFileDialog::open(receiver, member)

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
        self.ee.resultExportDirectoryChanged.connect(self.setResultExportDirectory)
        self.ee.signupListDirectoryChanged.connect(self.setSignupListDirectory)
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
        if self.modified:
            result = self.showUnsavedDialog()
            if result == QMessageBox.Save:
                self.saveFile()
            elif result == QMessageBox.Cancel:
                return False
        return True

    def _openDialog(self, slot):
        # equivalent of QFileDialog::open(this, SLOT(...))
        if self._dialogSlot is not None:
            try:
                self.dialog.fileSelected.disconnect(self._dialogSlot)
            except (RuntimeError, TypeError):
                pass
        self._dialogSlot = slot
        self.dialog.fileSelected.connect(slot)
        self.dialog.open()

    def openFile(self, filename=None):
        # C++ overloads: openFile() shows the dialog; openFile(QString) loads
        if filename is None:
            if self.okayToLoad():
                self.dialog.setAcceptMode(QFileDialog.AcceptOpen)
                self.dialog.setDirectory(resolved_search_path("events"))
                self._openDialog(self.openFile)
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

                path = QDir(filename)
                path.cdUp()
                self.eventDirectoryChanged.emit(path.canonicalPath())

    def rpList(self):
        self.rpe.updateData()
        return self.nw.rpList()

    def saveFile(self, filename=""):
        if filename == "":  # if no filename was specified
            if self.currentFileName == "":  # still “Untitled”?
                self.saveFileAs()
            else:
                filename = self.currentFileName

        from .xml.xmlwriter import XkorXmlWriter

        XkorXmlWriter(filename, self.rpList(), self.events())

        self.currentFileName = filename
        self.fileChanged.emit(filename)
        self.setModified(False)

        path = QDir(filename)
        path.cdUp()
        self.eventDirectoryChanged.emit(path.canonicalPath())

    def saveFileAs(self):
        self.dialog.setAcceptMode(QFileDialog.AcceptSave)
        self.dialog.setDirectory(resolved_search_path("events"))
        self._openDialog(self.saveFile)

    def setModified(self, isModified=True):
        self.modified = isModified
        if isModified:
            self.fileEdited.emit()

    def setResultExportDirectory(self, dir):
        self.resultExportDirectoryChanged.emit(dir)

    def setSignupListDirectory(self, dir):
        self.signupListDirectoryChanged.emit(dir)

    def showEventEditor(self, e):
        self.updateCurrentEvent()
        self.currentEvent = e
        self.ee.setData(e, self.rpList())
        self.editor.setCurrentWidget(self.ee)

    def showRPEditor(self):
        self.editor.setCurrentWidget(self.rpe)

    def showUnsavedDialog(self):
        displayFileName = "untitled" if self.currentFileName == "" else QFileInfo(self.currentFileName).fileName()
        warning = message_box(
            self, "Do you want to save the changes you made to “%s”?" % displayFileName,
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            informativeText="Your changes will be lost if you don’t save them.",
            destructiveButton=QMessageBox.Discard)
        return warning.exec()

    def updateCurrentEvent(self):
        if self.currentEvent is not None:
            # *currentEvent = ee->data(): copy the value into the existing object
            d = self.ee.data()  # data() returns a fresh copy
            e = self.currentEvent
            e.m_competition = d.m_competition
            e.m_competitionOptions = d.m_competitionOptions
            e.m_name = d.m_name
            e.m_groups = d.m_groups
            e.m_paradigm = d.m_paradigm
            e.m_paradigmOptions = d.m_paradigmOptions
            e.m_results = d.m_results
            e.m_signupList = d.m_signupList
            e.m_sport = d.m_sport
