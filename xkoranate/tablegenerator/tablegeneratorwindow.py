from PySide6.QtCore import QFileInfo, Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMainWindow, QToolBar

from .. import __version__
from ..help import help_action
from ..icons import icon_action
from .tablegenerator import XkorTableGenerator


class XkorTableGeneratorWindow(QMainWindow):
    resultImportDirectoryChanged = Signal(str)
    tableDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"untitled – xkoranate table generator {__version__}")

        self.generator = XkorTableGenerator()
        self.setCentralWidget(self.generator)
        self.generator.fileChanged.connect(self.setFileName)
        self.generator.fileEdited.connect(self.setModified)
        self.generator.resultImportDirectoryChanged.connect(self.setResultImportDirectory)
        self.generator.tableDirectoryChanged.connect(self.setTableDirectory)

        self.newAction = icon_action("document-new", "New file", self)
        self.newAction.setShortcut(QKeySequence.New)
        self.newAction.triggered.connect(lambda: self.generator.reset())

        self.openAction = icon_action("document-open", "Open file…", self)
        self.openAction.setShortcut(QKeySequence.Open)
        self.openAction.triggered.connect(lambda: self.generator.openFile())

        self.saveAction = icon_action("document-save", "Save file", self)
        self.saveAction.setShortcut(QKeySequence.Save)
        self.saveAction.triggered.connect(lambda: self.generator.saveFile())

        self.saveAsAction = icon_action("document-save-as", "Save file as…", self)
        self.saveAsAction.setShortcut(QKeySequence.SaveAs)
        self.saveAsAction.triggered.connect(lambda: self.generator.saveFileAs())

        self.importAction = icon_action("document-import", "Import match results…", self)
        self.importAction.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_I))
        self.importAction.triggered.connect(lambda: self.generator.importResults())

        self.generateAction = icon_action("table-generator-refresh", "Generate table", self)
        self.generateAction.setShortcut(QKeySequence.Refresh)
        self.generateAction.triggered.connect(lambda: self.generator.generateTable())

        # this window has no menu bar, so the action lives on the window
        # itself; the help key opens the guide's table generator page
        self.helpAction = help_action(self, "table-generator/")
        self.addAction(self.helpAction)

        self.toolBar = QToolBar()
        self.toolBar.setMovable(False)
        self.toolBar.addAction(self.newAction)
        self.toolBar.addAction(self.openAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.saveAction)
        self.toolBar.addAction(self.saveAsAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.importAction)
        self.toolBar.addAction(self.generateAction)

        self.addToolBar(self.toolBar)
        if hasattr(self, "setUnifiedTitleAndToolBarOnMac"):
            self.setUnifiedTitleAndToolBarOnMac(True)

    def closeEvent(self, event):
        if self.generator.close():
            QMainWindow.closeEvent(self, event)
        else:
            event.ignore()

    def setFileName(self, filename):
        displayName = "untitled"
        if filename != "":
            displayName = QFileInfo(filename).fileName()
        self.setWindowTitle(displayName + f"[*] – xkoranate table generator {__version__}")
        self.setModified(False)

    def setModified(self, newModified=True):
        self.setWindowModified(newModified)

    def setResultImportDirectory(self, dir):
        self.resultImportDirectoryChanged.emit(dir)

    def setTableDirectory(self, dir):
        self.tableDirectoryChanged.emit(dir)
