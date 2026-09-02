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
from PySide6.QtWidgets import QAbstractItemView, QApplication

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
