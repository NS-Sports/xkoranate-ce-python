"""The dropdown arrow shown on a selected row whose editor is a combo box."""

import pytest
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QStyle, QStyledItemDelegate,
                               QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem)

from xkoranate.eventeditor.eventsetupdelegate import XkorEventSetupDelegate
from xkoranate.rpeditor.rpbonuswidgets.wc36rpbonusdelegate import XkorWC36RPBonusDelegate
from xkoranate.tablegenerator.sortcriteriadelegate import XkorSortCriteriaDelegate
from xkoranate.ui.comboindicator import XkorComboIndicatorMixin


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class Indicated(XkorComboIndicatorMixin, QStyledItemDelegate):
    pass


class NotIndicated(XkorComboIndicatorMixin, QStyledItemDelegate):
    def usesComboEditor(self, index):
        return False


def render(delegate, selected):
    """Paint one row and hand back the pixels."""
    tree = QTreeWidget()
    tree.setColumnCount(1)
    QTreeWidgetItem(tree).setText(0, "Goals for")
    index = tree.model().index(0, 0)

    pixmap = QPixmap(160, 20)
    pixmap.fill(Qt.white)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 160, 20)
    option.state = QStyle.StateFlag.State_Enabled
    if selected:
        option.state |= QStyle.StateFlag.State_Selected

    painter = QPainter(pixmap)
    delegate.paint(painter, option, index)
    painter.end()
    return pixmap.toImage()


def test_a_selected_combo_row_is_drawn_differently_from_one_without(qapp):
    """Same row, same selection: the only difference is the arrow."""
    withArrow = render(Indicated(), selected=True)
    without = render(NotIndicated(), selected=True)
    assert withArrow != without


def test_nothing_is_drawn_when_the_row_is_not_selected(qapp):
    """The hint belongs where the user is looking, not on every row."""
    assert render(Indicated(), selected=False) == render(NotIndicated(), selected=False)


def test_the_sort_criteria_list_marks_every_row(qapp):
    delegate = XkorSortCriteriaDelegate([], [])
    assert delegate.usesComboEditor(QModelIndex())


def test_the_event_setup_list_marks_participants_but_not_group_names(qapp):
    delegate = XkorEventSetupDelegate([], [])
    tree = QTreeWidget()
    group = QTreeWidgetItem(tree)
    QTreeWidgetItem(group)
    groupIndex = tree.model().index(0, 0)
    athleteIndex = tree.model().index(0, 0, groupIndex)

    assert not delegate.usesComboEditor(groupIndex)  # a group name is free text
    assert delegate.usesComboEditor(athleteIndex)


def test_the_rp_bonus_list_marks_only_the_rating_column(qapp):
    delegate = XkorWC36RPBonusDelegate()
    tree = QTreeWidget()
    tree.setColumnCount(2)
    QTreeWidgetItem(tree)

    assert not delegate.usesComboEditor(tree.model().index(0, 0))
    assert delegate.usesComboEditor(tree.model().index(0, 1))
