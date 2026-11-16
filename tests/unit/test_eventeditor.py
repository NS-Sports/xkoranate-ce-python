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


def test_the_bracket_question_says_what_going_on_does(editor, monkeypatch):
    """Its Discard button reads "Don't Save" on macOS, which left the
    question with no way to go on."""
    from PySide6.QtWidgets import QMessageBox

    labels = []

    def answer(box):
        labels.append([b.text() for b in box.buttons()])
        return QMessageBox.Cancel

    monkeypatch.setattr(QMessageBox, "exec", answer)
    editor.m_data.setResults({0: "played"})

    assert editor.confirmDiscardBracketResults() is False
    assert len(labels) == 1 and "Discard Results" in labels[0]


# ------------------------------------- choosing a sport keeps the loaded format

@pytest.fixture
def unresolvedCup(tournament):
    """A cup of 12 (16 slots, four byes) with its first round played, saved
    under a sport name that isn't installed — renamed since, say."""
    from builders import play

    ev, sport = tournament("cup of 12")
    play(ev, sport, up_to=1)
    loaded = ev.clone()
    loaded.setSport(MISSING, sport.paradigm())
    return loaded, sport


def test_choosing_a_sport_keeps_the_loaded_competition_type(editor, unresolvedCup):
    """Loading with no sport fell back to the default type, and choosing a
    sport kept it: the knockout came back as a round robin."""
    loaded, _sport = unresolvedCup
    editor.setData(loaded, XkorRPList())

    editor.sportSelector.setSelectedSport(LISA)
    shown = editor.data()

    assert shown.sport() == LISA
    assert shown.competition() == "singleElimination"
    assert editor.competitionSelector.competition() == "singleElimination"
    assert shown.competitionOptions() == loaded.competitionOptions()
    assert shown.results() == loaded.results()


def test_choosing_a_sport_keeps_the_loaded_bracket(editor, unresolvedCup):
    """The fallback type laid the bracket out as groups, which drops byes, so
    a draw arranged by hand came back re-padded: the byes moved, and the round
    already played no longer described it."""
    from builders import new_competition, play

    from xkoranate.group import XkorGroup

    cup, sport = unresolvedCup
    # the editor's own layout, byes included, with each match's two slots
    # swapped: an arrangement only the saved slot list can reproduce
    installed = cup.clone()
    installed.setSport(LISA, sport.paradigm())
    installed.setResults({})
    editor.setData(installed, XkorRPList())
    slots = editor.data().groups()[0].athletes
    arranged = [s for i in range(0, len(slots), 2) for s in (slots[i + 1], slots[i])]
    installed.setGroups([XkorGroup("Bracket", arranged)])
    play(installed, sport, up_to=1)
    loaded = installed.clone()
    loaded.setSport(MISSING, sport.paradigm())

    editor.setData(loaded, XkorRPList())
    editor.sportSelector.setSelectedSport(LISA)
    shown = editor.data()

    assert shown.groups()[0].athletes == arranged
    assert new_competition(shown, sport).results(0) == loaded.results()[0]


def test_a_sport_without_the_loaded_type_keeps_its_own(editor, unresolvedCup, sport_index):
    """A race has no knockout: the selector's choice stands, and nothing raises."""
    from builders import SPRINT

    from xkoranate.xml.xmlsportreader import XkorXmlSportReader

    race = XkorXmlSportReader(sport_index.lookup(SPRINT)).sport().name()
    loaded, _sport = unresolvedCup
    editor.setData(loaded, XkorRPList())

    editor.sportSelector.setSelectedSport(race)

    assert editor.data().sport() == race
    assert editor.data().competition() == editor.competitionSelector.competition()
    assert editor.data().competition() != "singleElimination"


# ------------------------------------------- the bracket's discard question

BRACKET = 3  # the Groups/Bracket step


@pytest.fixture
def playedCup(editor, tournament, monkeypatch):
    """A cup of 8 with round one played, shown on its bracket page, and
    every "discard the results?" answered Discard and counted."""
    from builders import play

    from xkoranate.eventeditor import eventeditor

    ev, sport = tournament("cup of 8")
    play(ev, sport, up_to=1)
    editor.setData(ev, XkorRPList())
    while editor.stack.currentIndex() < BRACKET:
        editor.goNext()
    asked = []
    monkeypatch.setattr(eventeditor, "confirm", lambda *args, **kwargs: (asked.append(1), True)[1])
    return editor, asked


def test_discard_is_remembered_while_on_the_bracket_page(playedCup):
    editor, asked = playedCup

    editor.eventSetupWidget.seedBracket()
    editor.eventSetupWidget.randomizeGroup()
    editor.eventSetupWidget.seedBracket()

    assert asked == [1]


def test_results_played_after_leaving_the_page_are_asked_about_again(playedCup):
    """Discard used to be remembered for as long as the event stayed open,
    so a round played after it was thrown away by the next edit, unasked."""
    editor, asked = playedCup
    editor.eventSetupWidget.seedBracket()

    editor.goNext()  # to Scorinate, where round one is played again
    editor.setResult(0, "Round one, played again")
    editor.goPrev()
    editor.eventSetupWidget.randomizeGroup()

    assert asked == [1, 1]
