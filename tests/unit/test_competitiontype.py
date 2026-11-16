"""Results belong to the competition type that played them.

They are stored as text per matchday, beside resume options each type reads
its played matches back from. Nothing recorded which type wrote them, so a
switch showed one type's results under another's round names, and play went
on from them.
"""

import pytest
from builders import new_competition, play

from xkoranate.competitions.abstractcompetition import RESULTS_COMPETITION
from xkoranate.competitions.competitionfactory import XkorCompetitionFactory
from xkoranate.rplist import XkorRPList
from xkoranate.variant import toList

OTHER_TYPES = [t for t in XkorCompetitionFactory.competitionTypes() if t != "roundRobin"]


def switched(ev, competition):
    rval = ev.clone()
    rval.setCompetition(competition)
    return rval


def played(c):
    return [md for md in range(c.matchdays()) if c.results(md)]


@pytest.fixture
def league(tournament):
    """A round robin of three groups of four, two matchdays played."""
    ev, sport = tournament("league 3×4")
    play(ev, sport, up_to=2)
    return ev, sport


def test_scorinating_stamps_the_type(league):
    ev, _sport = league
    assert ev.competitionOptions()[RESULTS_COMPETITION] == "roundRobin"


@pytest.mark.parametrize("competition", OTHER_TYPES)
def test_another_types_results_are_not_shown(league, competition):
    ev, sport = league
    c = new_competition(switched(ev, competition), sport)

    assert played(c) == []


def test_a_knockout_does_not_go_on_from_a_leagues_results(qapp, league):
    """The scorinate page read the league's two matchdays as two rounds
    played, so the knockout's next scorination was its quarter-finals —
    stored as "The previous round hasn't been played yet." """
    from xkoranate.eventeditor.scorinatewidget import XkorScorinateWidget

    ev, sport = league
    w = XkorScorinateWidget()
    w.setEvent(switched(ev, "singleElimination"), XkorRPList(), sport)

    assert w.lastMatchday == -1
    assert w.c.matchdayNames()[0] == "Round of 16"


def test_switching_back_without_playing_finds_them_intact(league):
    ev, sport = league
    before = [new_competition(ev, sport).results(md) for md in range(2)]

    back = switched(switched(ev, "standard"), "roundRobin")

    assert [new_competition(back, sport).results(md) for md in range(2)] == before


def test_switching_back_after_playing_another_type_starts_clean(league):
    """The league's played matches stayed in its resume options, so the
    first matchday after switching back was added on top of them."""
    ev, sport = league
    other = switched(ev, "matches")
    play(other, sport)
    back = switched(other, "roundRobin")

    c = play(back, sport, up_to=1)

    assert played(c) == [0]
    perGroup = [len(toList(g)) for g in toList(back.competitionOptions()["tableData"])]
    assert perGroup == [2, 2, 2]  # one matchday: two matches in each group of four


@pytest.mark.parametrize("competition", list(XkorCompetitionFactory.competitionTypes()))
def test_every_type_names_the_resume_keys_it_writes(tournament, competition):
    """A switch drops exactly these, so one left out would survive it."""
    ev, sport = tournament("league 3×4")
    c = new_competition(switched(ev, competition), sport)
    if c.matchdays() <= 0:
        pytest.skip("nothing to play for this type here")
    c.scorinate(0)

    written = set(c.resumeFileOptions()) - {RESULTS_COMPETITION}
    assert written <= set(c.resumeKeys)


def test_switching_to_multiple_run_ignores_shootings_scores(tournament):
    """Both types keep a "scores" option, in different shapes. The switch
    used to run multiple-run's revert over shooting's shorter list, which
    raised IndexError while the event was being opened."""
    ev, sport = tournament("league 3×4")
    ids = [str(a.id) for g in ev.makeStartList(XkorRPList()).groups for a in g.athletes]
    options = ev.competitionOptions()
    options.update({
        # left by an earlier multiple-run scorination of everyone
        "athletes": ids, "scoreStrings": [["1"]] * len(ids),
        # then overwritten by a shooting qualifying round with a cutoff
        "scores": [9.5] * 4, "qualifiers": ids[:4],
        RESULTS_COMPETITION: "shooting",
    })
    ev.setCompetitionOptions(options)
    ev.setResults({0: "shooting results"})

    c = new_competition(switched(ev, "multipleRun"), sport)

    assert played(c) == []
    assert "scores" not in c.userOpt and "athletes" not in c.userOpt


def test_results_saved_before_the_stamp_are_kept(league):
    """Files saved by earlier versions have no stamp to go by."""
    ev, sport = league
    options = ev.competitionOptions()
    del options[RESULTS_COMPETITION]
    ev.setCompetitionOptions(options)

    assert played(new_competition(ev, sport)) == [0, 1]


@pytest.fixture
def answers(monkeypatch):
    """Every question the scorinate page asks, answered from `answers.reply`."""
    from xkoranate.eventeditor import scorinatewidget

    class Answers(list):
        reply = True

    asked = Answers()
    monkeypatch.setattr(scorinatewidget, "confirm",
                        lambda parent, text, *args, **kwargs: (asked.append(text), asked.reply)[1])
    return asked


def scorinate_page(ev, sport):
    from xkoranate.eventeditor.scorinatewidget import XkorScorinateWidget

    w = XkorScorinateWidget()
    w.setEvent(ev, XkorRPList(), sport)
    confirmed = []
    w.resultConfirmed.connect(lambda md, text: confirmed.append(md))
    return w, confirmed


def test_another_types_results_are_shown_as_kept(qapp, league):
    """Hidden, not lost: an empty pane alone read as the results being gone."""
    ev, sport = league
    w, _confirmed = scorinate_page(switched(ev, "singleElimination"), sport)

    assert w.textedit.toPlainText() == ""
    assert "Round robin" in w.textedit.placeholderText()


def test_replacing_another_types_results_asks_first(qapp, league, answers):
    ev, sport = league
    w, confirmed = scorinate_page(switched(ev, "singleElimination"), sport)
    answers.reply = False

    w.scorinate()

    assert answers == ["Replace the results played as “Round robin”?"]
    assert confirmed == []
    assert [w.e.results()[md] for md in range(2)] == [ev.results()[md] for md in range(2)]


def test_replacing_them_asks_only_once(qapp, league, answers):
    ev, sport = league
    w, confirmed = scorinate_page(switched(ev, "singleElimination"), sport)

    w.scorinate()
    w.matchday.setCurrentIndex(1)
    w.scorinate()

    assert answers == ["Replace the results played as “Round robin”?"]
    assert confirmed == [0, 1]
    assert w.textedit.placeholderText() == ""


def test_scorinating_the_same_type_does_not_ask(qapp, league, answers):
    ev, sport = league
    w, confirmed = scorinate_page(ev, sport)
    w.matchday.setCurrentIndex(2)

    w.scorinate()

    assert answers == []
    assert confirmed == [2]
    assert w.textedit.placeholderText() == ""
