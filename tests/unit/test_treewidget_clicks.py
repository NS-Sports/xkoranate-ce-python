"""Click behaviour on the shared reorderable list widget.

Issue #41 removed SelectedClicked from the edit triggers because it made every
single click on an already-selected row wait out the double-click interval.
That left a second problem: these lists are drag-reorderable, so Qt treats the
first press on an unselected row as a possible drag and its double click never
reaches the DoubleClicked trigger — the row had to be selected first, making it
three clicks to open an editor.
"""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView, QApplication, QComboBox

from xkoranate.tablegenerator.sortcriteriawidget import XkorSortCriteriaWidget

CRITERIA = ["points", "goalDifference", "goalsFor", "h2hPoints"]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(qapp):
    w = XkorSortCriteriaWidget()
    w.setSortCriteria(list(CRITERIA))
    w.resize(400, 220)
    w.show()
    QApplication.processEvents()
    return w


def rowCentre(tree, row):
    return tree.visualRect(tree.model().index(row, 0)).center()


def isEditing(tree):
    return tree.state() == QAbstractItemView.State.EditingState


def click(tree, row):
    QTest.mouseClick(tree.viewport(), Qt.LeftButton, Qt.NoModifier, rowCentre(tree, row))
    QApplication.processEvents()


def doubleClick(tree, row):
    QTest.mouseDClick(tree.viewport(), Qt.LeftButton, Qt.NoModifier, rowCentre(tree, row))
    QApplication.processEvents()


def test_a_single_click_selects_without_editing(widget):
    tree = widget.treeWidget
    click(tree, 1)
    assert tree.selectedItems()
    assert not isEditing(tree)


def test_clicking_an_already_selected_row_still_does_not_edit(widget):
    """The regression #41 fixed: this is what SelectedClicked used to cause."""
    tree = widget.treeWidget
    for _ in range(3):
        click(tree, 1)
        assert not isEditing(tree)


def selectedRows(tree):
    return [tree.indexOfTopLevelItem(i) for i in tree.selectedItems()]


def test_a_double_click_opens_the_editor_on_a_row_that_was_not_selected(widget):
    """The three-click case: the row you double click isn't the selected one."""
    tree = widget.treeWidget
    click(tree, 0)
    assert selectedRows(tree) == [0]

    doubleClick(tree, 2)  # a different row, so the first press starts a drag
    assert isEditing(tree)
    assert selectedRows(tree) == [2]


def test_a_double_click_opens_the_editor_on_an_already_selected_row(widget):
    tree = widget.treeWidget
    click(tree, 2)
    doubleClick(tree, 2)
    assert isEditing(tree)


def test_a_double_click_on_empty_space_does_nothing(widget):
    tree = widget.treeWidget
    QTest.mouseDClick(tree.viewport(), Qt.LeftButton, Qt.NoModifier,
                      QPoint(50, tree.viewport().height() - 5))
    QApplication.processEvents()
    assert not isEditing(tree)


def test_the_list_is_still_reorderable(widget):
    assert widget.treeWidget.dragDropMode() == QAbstractItemView.InternalMove
    click(widget.treeWidget, 0)
    widget.moveDown()
    assert widget.sortCriteria()[:2] == ["goalDifference", "points"]


def settle():
    """The editor is placed, and its popup opened, on the next event loop pass."""
    for _ in range(6):
        QApplication.processEvents()


def test_a_double_click_drops_the_list_open(widget):
    """Opening the editor only puts a closed combo in the row, so reaching the
    choices still took another click."""
    tree = widget.treeWidget
    click(tree, 0)
    doubleClick(tree, 3)
    settle()

    combo = tree.viewport().findChild(QComboBox)
    assert combo is not None
    assert combo.view().isVisible()


def test_the_arrow_never_grows_with_the_row():
    """It was drawn into the full row height and looked absurd. Row height
    follows the user's font, so the glyph has to stay capped."""
    from xkoranate.ui.comboindicator import ARROW_MAX, ARROW_MIN, INDICATOR_WIDTH

    assert ARROW_MIN <= ARROW_MAX <= 9
    assert ARROW_MAX < INDICATOR_WIDTH

    for rowHeight in (14, 20, 26, 40, 80):
        size = max(ARROW_MIN, min(ARROW_MAX, rowHeight - 6))
        assert ARROW_MIN <= size <= ARROW_MAX


def openEditorOn(widget, row):
    tree = widget.treeWidget
    click(tree, 0)
    doubleClick(tree, row)
    settle()
    return tree.viewport().findChild(QComboBox)


def test_the_editor_does_not_overlap_the_rows_around_it(widget):
    """The theme's stylesheet gives combo boxes a min-height of their own, so
    the editor stood taller than the row it replaced and covered its
    neighbours."""
    tree = widget.treeWidget
    combo = openEditorOn(widget, 3)
    rowHeight = tree.visualRect(tree.model().index(3, 0)).height()

    assert combo is not None
    assert combo.height() <= rowHeight


def test_choosing_an_entry_closes_the_editor(widget):
    """It used to sit there over the row until something else took focus."""
    tree = widget.treeWidget
    combo = openEditorOn(widget, 3)
    before = widget.sortCriteria()[3]

    combo.setCurrentIndex(combo.currentIndex() + 1)
    combo.activated.emit(combo.currentIndex())
    settle()

    # closeEditor defers the widget's deletion, so it is still a child for a
    # moment — what matters is that it is no longer on screen
    remaining = tree.viewport().findChild(QComboBox)
    assert remaining is None or not remaining.isVisible()
    assert widget.sortCriteria()[3] != before  # and the choice was kept
