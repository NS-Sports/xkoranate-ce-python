from PySide6.QtCore import QDir, QFileInfo, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QApplication, QToolBar

from . import __version__
from .centralwidget import XkorCentralWidget
from .help import help_action
from .icons import icon, icon_action
from .mainwindow import XkorMainWindow
from .paths import appSettings, sportsDir
from . import theme
from .variant import toStringList

# (search path prefix, settings key) for each directory the app remembers
_DIRECTORIES = [
    ("events", "eventDirectory"),
    ("resultsExport", "resultExportDirectory"),
    ("resultsImport", "resultImportDirectory"),
    ("signupLists", "signupListDirectory"),
    ("tables", "tableDirectory"),
]


class XkorApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        # flat light/dark theme — must be applied before any widgets are
        # constructed so themed palettes/metrics are in place from the start
        theme.apply(self)

        self.tg = None
        self.modified = False

        self.settings = appSettings()

        self.setDefaultSettings()  # in case we haven’t run the application before

        self.mainWindow = XkorMainWindow()
        if hasattr(self.mainWindow, "setUnifiedTitleAndToolBarOnMac"):
            self.mainWindow.setUnifiedTitleAndToolBarOnMac(True)

        self.cw = XkorCentralWidget()
        self.cw.eventDirectoryChanged.connect(self.setEventDirectory)
        self.cw.fileChanged.connect(self.setFileName)
        self.cw.fileEdited.connect(self.setModified)
        self.cw.resultExportDirectoryChanged.connect(self.setResultExportDirectory)
        self.cw.signupListDirectoryChanged.connect(self.setSignupListDirectory)

        # set up actions
        self.newAction = icon_action("document-new", "New file…", self)
        self.newAction.setShortcut(QKeySequence(QKeySequence.New))
        self.newAction.triggered.connect(lambda: self.cw.newFile())

        self.openAction = icon_action("document-open", "Open file…", self)
        self.openAction.setShortcut(QKeySequence(QKeySequence.Open))
        self.openAction.triggered.connect(lambda: self.cw.openFile())

        self.saveAction = icon_action("document-save", "Save file…", self)
        self.saveAction.setShortcut(QKeySequence(QKeySequence.Save))
        self.saveAction.triggered.connect(lambda: self.cw.saveFile())

        self.saveAsAction = icon_action("document-save-as", "Save file as…", self)
        self.saveAsAction.setShortcut(QKeySequence(Qt.CTRL | Qt.SHIFT | Qt.Key_S))
        self.saveAsAction.triggered.connect(lambda: self.cw.saveFileAs())

        self.tableAction = icon_action("table-generator", "Table generator", self)
        self.tableAction.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_T))
        self.tableAction.triggered.connect(self.tableGenerator)

        self.quitAction = QAction("Quit", self)
        self.quitAction.setShortcut(QKeySequence(QKeySequence.Quit))
        self.quitAction.triggered.connect(self.closeAllWindows)

        self.helpAction = help_action(self)

        # View menu's theme choice — light/dark/OLED are mutually exclusive,
        # so a QActionGroup gives us the radio-button behaviour for free
        self.themeActionGroup = QActionGroup(self)
        self.themeActionGroup.setExclusive(True)
        self.themeActions = {}
        currentMode = theme.mode()
        for themeMode in theme.MODES:
            action = QAction(theme.MODE_LABELS[themeMode], self)
            action.setCheckable(True)
            action.setChecked(themeMode == currentMode)
            action.triggered.connect(lambda checked, m=themeMode: theme.set_mode(self, m))
            self.themeActionGroup.addAction(action)
            self.themeActions[themeMode] = action
        # keep the menu's radio selection in sync if the theme changes some
        # other way (e.g. restored from settings on next launch)
        theme.signal.changed.connect(self._syncThemeActions)

        # menu bar — the standard cross-platform place shortcuts are
        # discoverable; the toolbar's icons/tooltips don't show them
        menuBar = self.mainWindow.menuBar()
        fileMenu = menuBar.addMenu("&File")
        fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.saveAsAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.tableAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.quitAction)

        viewMenu = menuBar.addMenu("&View")
        for themeMode in theme.MODES:
            viewMenu.addAction(self.themeActions[themeMode])

        # a menu titled "Help" is what macOS (and most users) look for; Qt
        # moves it to the far right on every platform
        helpMenu = menuBar.addMenu("&Help")
        helpMenu.addAction(self.helpAction)

        # toolbar
        self.toolBar = QToolBar()
        self.toolBar.setMovable(False)
        self.toolBar.addAction(self.newAction)
        self.toolBar.addAction(self.openAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.saveAction)
        self.toolBar.addAction(self.saveAsAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.tableAction)

        self.mainWindow.setCentralWidget(self.cw)
        self.mainWindow.addToolBar(self.toolBar)
        self.mainWindow.setWindowTitle(f"untitled[*] – xkoranate {__version__}")

        # C++ only did this on X11; on macOS the .app bundle provides the dock
        # icon, so setting it unconditionally is harmless
        self.mainWindow.setWindowIcon(icon("xkoranate"))

        self.mainWindow.show()

    def loadSports(self):
        self.refreshSearchPaths()
        self.cw.loadSports()

    # bool notify(QObject *, QEvent *) is not ported: Python exceptions
    # propagate fine without it

    def refreshSearchPaths(self):
        QDir.setSearchPaths("sports", [sportsDir()])

        for prefix, key in _DIRECTORIES:
            QDir.setSearchPaths(prefix, toStringList(self.settings.value(key)))

    def setDefaultSettings(self):
        for _prefix, key in _DIRECTORIES:
            if not self.settings.contains(key):
                self._setDirectory(key, QDir.homePath())

    def _setDirectory(self, key, dir):
        self.settings.setValue(key, dir)
        self.refreshSearchPaths()

    def setEventDirectory(self, dir):
        self._setDirectory("eventDirectory", dir)

    def setFileName(self, filename):
        displayName = "untitled"
        if filename != "":
            displayName = QFileInfo(filename).fileName()
        self.mainWindow.setWindowTitle(displayName + f"[*] – xkoranate {__version__}")
        self.setModified(False)

    def setModified(self, newModified=True):
        self.modified = newModified
        self.mainWindow.setWindowModified(newModified)

    def _syncThemeActions(self):
        action = self.themeActions.get(theme.mode())
        if action is not None:
            action.setChecked(True)

    def setResultExportDirectory(self, dir):
        self._setDirectory("resultExportDirectory", dir)

    def setResultImportDirectory(self, dir):
        self._setDirectory("resultImportDirectory", dir)

    def setSignupListDirectory(self, dir):
        self._setDirectory("signupListDirectory", dir)

    def setTableDirectory(self, dir):
        self._setDirectory("tableDirectory", dir)

    def tableGenerator(self):
        from .tablegenerator.tablegeneratorwindow import XkorTableGeneratorWindow

        if self.tg is not None:  # delete tg
            self.tg.close()
            self.tg.deleteLater()
        self.tg = XkorTableGeneratorWindow()
        self.tg.resultImportDirectoryChanged.connect(self.setResultImportDirectory)
        self.tg.tableDirectoryChanged.connect(self.setTableDirectory)
        self.tg.show()
