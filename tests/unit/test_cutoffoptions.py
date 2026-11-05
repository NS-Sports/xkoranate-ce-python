"""The archery and shooting cutoff boxes: the text under the spin box."""

import pytest

from xkoranate.competitions.options.archerycompetitionoptions import XkorArcheryCompetitionOptions
from xkoranate.competitions.options.shootingcompetitionoptions import XkorShootingCompetitionOptions

WIDGETS = [XkorArcheryCompetitionOptions, XkorShootingCompetitionOptions]


@pytest.mark.parametrize("cls", WIDGETS)
def test_a_new_event_shows_the_initial_text(qapp, cls):
    assert cls({}).explanation.text() == cls.initialText


@pytest.mark.parametrize("cls", WIDGETS)
def test_a_saved_cutoff_is_explained_on_load(qapp, cls):
    widget = cls({"cutoff": 8})

    # was the no-cutoff text until the spin box was touched
    assert widget.explanation.text() == cls.cutoffText % "8th"


@pytest.mark.parametrize("cls", WIDGETS)
def test_a_saved_cutoff_of_all_is_explained_on_load(qapp, cls):
    assert cls({"cutoff": 0}).explanation.text() == cls.noCutoffText


@pytest.mark.parametrize("cls", WIDGETS)
def test_changing_the_cutoff_changes_the_text(qapp, cls):
    widget = cls({"cutoff": 8})

    widget.cutoff.setValue(3)

    assert widget.explanation.text() == cls.cutoffText % "3rd"
    assert widget.options["cutoff"] == 3
