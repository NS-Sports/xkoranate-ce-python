from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QTreeWidget


class XkorTreeWidget(QTreeWidget):
    def mouseDoubleClickEvent(self, event):
        """Open the editor on any double click, selected row or not.

        These lists are drag-reorderable, and Qt treats the first press on an
        unselected row as the start of a possible drag — so its double click
        selects the row but never reaches the DoubleClicked edit trigger. The
        row had to be selected first, making it three clicks to open an editor
        on a row you hadn't already picked. Issue #41 removed SelectedClicked
        because it made ordinary single clicks wait out the double-click
        interval; asking for the edit explicitly here gets the double click
        working without bringing that lag back.
        """
        index = self.indexAt(event.position().toPoint())
        super().mouseDoubleClickEvent(event)

        if not index.isValid():
            return
        if not (self.editTriggers() & QAbstractItemView.EditTrigger.DoubleClicked):
            return
        if self.state() != QAbstractItemView.State.EditingState:
            self.edit(index)
        self.dropDownEditor()

    def dropDownEditor(self):
        """Drop the list open if the editor that just opened is a combo box.

        Opening the editor only puts a closed combo in the row, so reaching
        the actual choices still took another click. Deferred, because the
        editor isn't placed and shown until the view gets back to its event
        loop.
        """
        QTimer.singleShot(0, self._showEditorPopup)

    def _showEditorPopup(self):
        editor = self.viewport().findChild(QComboBox)
        if editor is not None and editor.isVisible():
            editor.showPopup()

    def moveCursor(self, cursorAction, modifiers):
        index = self.currentIndex()
        if cursorAction == QAbstractItemView.CursorAction.MoveNext:
            if index.column() < self.columnCount() - 1:
                return self.model().index(index.row(), index.column() + 1, index.parent())
        elif cursorAction == QAbstractItemView.CursorAction.MovePrevious:
            if index.column() > 0:
                return self.model().index(index.row(), index.column() - 1, index.parent())
        # in all other cases, let Qt do the hard work
        return QTreeWidget.moveCursor(self, cursorAction, modifiers)
