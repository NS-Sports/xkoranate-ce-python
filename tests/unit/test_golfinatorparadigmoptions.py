"""The golf course table: what editing a cell writes to the options."""

import pytest
from PySide6.QtWidgets import QTableWidgetItem

from xkoranate.paradigms.options.golfinatorparadigmoptions import XkorGolfinatorParadigmOptions

YARDS, PAR, GREEN = 0, 1, 6


@pytest.fixture
def widget(qapp):
    return XkorGolfinatorParadigmOptions({})


def edit(widget, row, column, text):
    """Type into a cell, as the user does; a cell past the end of a short
    saved list starts out with no item."""
    item = widget.course.item(row, column)
    if item is None:
        widget.course.setItem(row, column, QTableWidgetItem(text))
    else:
        item.setText(text)


def test_editing_a_hole_changes_that_hole_only(widget):
    edit(widget, 2, YARDS, "210")

    yardage = widget.options["yardage"]
    assert len(yardage) == 18  # was 19: the edit was inserted
    assert yardage[:4] == [435, 529, 210, 517]
    assert yardage[3:] == widget.defaultValue("yardage")[3:]


def test_editing_the_green_column_writes_what_the_paradigm_reads(widget):
    edit(widget, 0, GREEN, "1")

    assert widget.options["green"][0] == 1  # was stored as "grass"
    assert "grass" not in widget.options


def test_a_short_saved_list_fills_in_from_the_defaults(qapp):
    widget = XkorGolfinatorParadigmOptions({"par": [3, 3]})

    edit(widget, 4, PAR, "5")

    assert widget.options["par"] == [3, 3, 3, 5, 5]
