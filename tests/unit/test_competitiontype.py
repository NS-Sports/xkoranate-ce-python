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


def test_results_saved_before_the_stamp_are_kept(league):
    """Files saved by earlier versions have no stamp to go by."""
    ev, sport = league
    options = ev.competitionOptions()
    del options[RESULTS_COMPETITION]
    ev.setCompetitionOptions(options)

    assert played(new_competition(ev, sport)) == [0, 1]
