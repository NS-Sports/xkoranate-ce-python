import sys

from PySide6.QtCore import QItemSelectionModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLineEdit, QTreeView, QWidget

from ..exceptions import XkorFileNotFoundException
from ..sport import XkorSport
from ..ui.typography import heading_label
from .sportmodel import SPORT_DATA, SPORT_NAME, XkorSportModel


class XkorSportSelector(QWidget):
    paradigmOptionsChanged = Signal(dict)
    sportChanged = Signal(object)  # XkorSport

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.paradigmOptionsWidget = None
        self.selectionModel = None
        self.isLoading = False
        self.currentParadigmOptions = {}
        self._model = None  # keep a Python reference to the view's model

        self.sportView = QTreeView()
        self.sportView.setHeaderHidden(True)

        self.searchBox = QLineEdit()
        self.searchBox.setPlaceholderText("Search sports")
        self.searchBox.setToolTip(
            "Filter the list by discipline, event or scorinator name, "
            "e.g. \"Wrestling\"")
        self.searchBox.setClearButtonEnabled(True)
        self.searchBox.textChanged.connect(self.applyFilter)

        self.layout = QGridLayout(self)
        label = heading_label("Select sport", level=1, center=True)
        self.layout.addWidget(label, 0, 0, Qt.AlignCenter)
        self.layout.addWidget(self.searchBox, 1, 0)
        self.layout.addWidget(self.sportView, 2, 0)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def applyFilter(self):
        # hide rows that don't match, keeping the ancestors of any match
        # visible so the selected sport is still reachable
        text = self.searchBox.text().strip().lower()
        model = self.sportView.model()
        if model is None:
            return
        self._filterRows(model, QModelIndex(), text)
        if text:
            self.sportView.expandAll()
        else:
            self.sportView.collapseAll()
            self.setSelectedSport(self.sport().name())

    def _filterRows(self, model, parent, text):
        # returns True if this subtree contains a match (or there's no filter)
        anyVisible = False
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            selfMatch = not text or text in (index.data() or "").lower()
            # descendants of a matching row stay visible in their entirety
            childMatch = self._filterRows(model, index, "" if selfMatch else text)
            visible = selfMatch or childMatch
            self.sportView.setRowHidden(row, parent, not visible)
            anyVisible = anyVisible or visible
        return anyVisible

    def setParadigmOptions(self, paradigmOptions):
        self.currentParadigmOptions = paradigmOptions
        if self.paradigmOptionsWidget:
            self.paradigmOptionsWidget.setOptions(paradigmOptions)

    def setSelectedSport(self, fullNameOrIndex):
        # C++ overloads: setSelectedSport(QString) and setSelectedSport(QModelIndex)
        if isinstance(fullNameOrIndex, QModelIndex):
            index = fullNameOrIndex
        else:
            index = self.sportView.model().findSport(fullNameOrIndex)

        if index.isValid():
            self.sportView.scrollTo(index)
            self.selectionModel.select(index, QItemSelectionModel.ClearAndSelect)
            if index.parent() != QModelIndex():
                self.sportView.setExpanded(index.parent(), True)
                if index.parent().parent() != QModelIndex():
                    self.sportView.setExpanded(index.parent().parent(), True)
        else:
            self.sportView.clearSelection()
        self.updateSport()

    def sport(self):
        rval = XkorSport()
        if self.selectionModel:
            l = self.selectionModel.selectedRows()
            for i in l:
                if i.data(SPORT_NAME) is not None:
                    rval = i.data(SPORT_DATA)
        else:
            rval = XkorSport()
        return rval

    def updateParadigmOptions(self, paradigmOptions):
        self.currentParadigmOptions = paradigmOptions
        self.paradigmOptionsChanged.emit(paradigmOptions)

    def updateSport(self):
        s = self.sport()
        if not self.isLoading:
            self.sportChanged.emit(s)

        if self.paradigmOptionsWidget:
            self.layout.removeWidget(self.paradigmOptionsWidget)
            self.paradigmOptionsWidget.setParent(None)
            self.paradigmOptionsWidget.deleteLater()
        self.paradigmOptionsWidget = None

        # check whether the paradigm has an options dialog
        from ..paradigms.paradigmfactory import XkorParadigmFactory

        # initialize with the sport (not just the type) so paradigms whose
        # options widget needs a sport-file default — e.g. home advantage
        # magnitude — can read it from self.opt instead of guessing
        p = XkorParadigmFactory.newParadigmForSport(s, self.currentParadigmOptions)

        if s.name() != "" and p.hasOptionsWidget():
            self.paradigmOptionsWidget = p.newOptionsWidget(self.currentParadigmOptions)
            self.layout.addWidget(self.paradigmOptionsWidget)
            self.paradigmOptionsWidget.show()
            self.paradigmOptionsWidget.optionsChanged.connect(self.updateParadigmOptions)

    def updateSportList(self):
        self.isLoading = True
        try:
            sportName = self.sport().name()

            # create a model
            model = XkorSportModel()
            self.sportView.setModel(model)
            self._model = model

            self.selectionModel = QItemSelectionModel(model)
            self.sportView.setSelectionModel(self.selectionModel)
            self.selectionModel.selectionChanged.connect(self.updateSport)

            # load the sports
            from ..xml.xmlindex import XkorXmlIndex
            from ..xml.xmlsportreader import XkorXmlSportReader

            x = XkorXmlIndex()
            x.traverse("sports:./")

            s = x.getAllFiles()
            for key in sorted(s):  # std::map iterates in sorted-key order
                r = XkorXmlSportReader(s[key])
                model.insertSport(r.sport())
            self.sportView.reset()

            self.setSelectedSport(sportName)
            self.applyFilter()
        except XkorFileNotFoundException as ex:
            print("caught XkorFileNotFoundException in XkorSportSelector::updateSportList for",
                  ex.fileType(), " file ", ex.fileName(), file=sys.stderr)
        self.isLoading = False
