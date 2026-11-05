"""Importing participants from a text file, and what a failed import leaves."""

import pytest
from builders import make_athletes

from xkoranate.signuplisteditor.athletewidget import XkorAthleteWidget


@pytest.fixture
def widget(qapp):
    w = XkorAthleteWidget(["name", "nation", "skill"], ["Participant", "Team", "Skill"],
                          ["string", "string", "skill"])
    w.setAthletes(make_athletes(2))
    return w


def edits_are_saved(widget):
    """Whether an edit to the list still reaches the event."""
    changes = []
    widget.listChanged.connect(lambda: changes.append(True))
    widget.treeWidget.topLevelItem(0).setText(0, "Renamed")
    return bool(changes)


def test_importing_a_file_adds_its_participants(widget, tmp_path):
    f = tmp_path / "signups.txt"
    f.write_text("Alpha;AAA;0.4\nBravo;BBB;0.6\n", encoding="utf-8")

    widget.importAthletes(str(f))

    assert sorted(a.name for a in widget.athletes())[:2] == ["Alpha", "Athlete 1"]
    assert len(widget.athletes()) == 4
    assert edits_are_saved(widget)


def test_a_missing_file_imports_nothing_and_leaves_edits_saved(widget, tmp_path):
    widget.importAthletes(str(tmp_path / "missing.txt"))

    assert len(widget.athletes()) == 2
    assert edits_are_saved(widget)  # was lost: the import left isInUse set


def test_a_file_that_is_not_utf8_imports_nothing_and_leaves_edits_saved(widget, tmp_path):
    f = tmp_path / "signups.txt"
    f.write_bytes("Zoë;AAA;0.4\n".encode("latin-1"))

    widget.importAthletes(str(f))  # was an uncaught UnicodeDecodeError

    assert len(widget.athletes()) == 2
    assert edits_are_saved(widget)
