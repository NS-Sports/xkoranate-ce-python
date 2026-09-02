"""The knockout options widget: the third-place checkbox and what it writes."""

import pytest

from PySide6.QtCore import Qt

from xkoranate.competitions.options.singleeliminationcompetitionoptions import (
    XkorSingleEliminationCompetitionOptions)


@pytest.fixture
def widget(qapp):
    return XkorSingleEliminationCompetitionOptions({})


def test_the_playoff_is_off_by_default(widget):
    assert not widget.thirdPlace.isChecked()
    assert widget.options["thirdPlacePlayoff"] == "false"


def test_ticking_the_box_writes_the_option(widget):
    """Only ever set through the options dict before, so the handler — and
    the Qt.CheckState normalisation it exists for — never ran. PySide6 hands
    stateChanged an enum on some versions and an int on others; if that
    breaks on an upgrade, the whole feature is unreachable from the GUI with
    the suite still green."""
    emitted = []
    widget.optionsChanged.connect(lambda opts: emitted.append(dict(opts)))

    widget.thirdPlace.setChecked(True)
    assert widget.options["thirdPlacePlayoff"] == "true"
    assert emitted and emitted[-1]["thirdPlacePlayoff"] == "true"

    widget.thirdPlace.setChecked(False)
    assert widget.options["thirdPlacePlayoff"] == "false"


@pytest.mark.parametrize("value", [2, Qt.CheckState.Checked])
def test_the_handler_takes_an_enum_or_an_int(widget, value):
    widget.setThirdPlacePlayoff(value)
    assert widget.options["thirdPlacePlayoff"] == "true"


def test_an_existing_option_is_read_back(qapp):
    widget = XkorSingleEliminationCompetitionOptions({"thirdPlacePlayoff": "true"})
    assert widget.thirdPlace.isChecked()
