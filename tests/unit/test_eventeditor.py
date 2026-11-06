"""The event editor's wizard: what showing an event does to it, and which
steps the Go Back and Continue buttons allow."""

import pytest
from builders import LISA, make_athletes, make_event

from xkoranate.event import XkorEvent
from xkoranate.rplist import XkorRPList

MISSING = "Some custom sport—not installed"
SCORINATE = 4  # the last step


@pytest.fixture
def editor(qapp):
    from xkoranate.eventeditor.eventeditor import XkorEventEditor

    ee = XkorEventEditor()
    ee.loadSports()
    return ee


def buttons(ee):
    return ee.stack.currentIndex(), ee.prev.isEnabled(), ee.next.isEnabled()


# --------------------------------------------------- showing leaves it alone

def test_showing_an_event_with_a_missing_sport_leaves_it_alone(editor):
    """A sport that isn't installed can't be selected, so the selectors fell
    back to "no sport" and wrote that, and their default competition type,
    into the event — selecting it in the sidebar was enough for the next
    save to lose both."""
    ev = make_event(make_athletes(4), sport=MISSING, paradigm="lisa", competition="roundRobin",
                    options={"numberOfLegs": "2"})
    ev.setResults({0: "Matchday 1"})

    editor.setData(ev, XkorRPList())
    shown = editor.data()

    assert shown.sport() == MISSING
    assert shown.paradigm() == "lisa"
    assert shown.competition() == "roundRobin"
    assert shown.competitionOptions() == {"numberOfLegs": "2"}
    assert shown.results() == {0: "Matchday 1"}
    assert [a.id for a in shown.signupList().athletes()] == [a.id for a in ev.signupList().athletes()]
    assert (shown.signupList().minRank(), shown.signupList().maxRank()) \
        == (ev.signupList().minRank(), ev.signupList().maxRank())
    assert [g.athletes for g in shown.groups()] == [g.athletes for g in ev.groups()]
    # and there's no going on to scorinate it with no sport
    assert buttons(editor) == (0, False, False)


def test_choosing_a_sport_for_it_takes_over(editor):
    editor.setData(make_event(make_athletes(4), sport=MISSING, paradigm="lisa"), XkorRPList())

    editor.sportSelector.setSelectedSport(LISA)

    assert editor.data().sport() == LISA
    assert editor.next.isEnabled()


def test_an_installed_sport_is_still_read_from_the_editor(editor):
    ev = make_event(make_athletes(4), sport=LISA, paradigm="lisa", competition="roundRobin")
    editor.setData(ev, XkorRPList())
    editor.updateCompetition("matches")

    assert editor.data().competition() == "matches"


# ------------------------------------------------------------ the buttons

def test_loading_an_event_resets_go_back(editor):
    """setData() went back to the first step but left Go Back enabled, and
    Go Back on the first step then enabled Continue with no sport chosen."""
    editor.setData(make_event(make_athletes(4), sport=LISA, paradigm="lisa"), XkorRPList())
    editor.goNext()
    assert buttons(editor) == (1, True, True)

    editor.setData(XkorEvent(), XkorRPList())  # a new event: no sport yet
    assert buttons(editor) == (0, False, False)

    editor.goPrev()
    assert buttons(editor) == (0, False, False)


def test_continue_follows_the_sport_and_stops_at_the_last_step(editor):
    editor.setData(XkorEvent(), XkorRPList())
    assert buttons(editor) == (0, False, False)

    editor.sportSelector.setSelectedSport(LISA)
    assert buttons(editor) == (0, False, True)

    for step in range(1, SCORINATE + 1):
        editor.goNext()
        assert buttons(editor) == (step, True, step < SCORINATE)

    for step in reversed(range(SCORINATE)):
        editor.goPrev()
        assert buttons(editor) == (step, step > 0, True)

    editor.sportSelector.setSelectedSport("")
    assert buttons(editor) == (0, False, False)
