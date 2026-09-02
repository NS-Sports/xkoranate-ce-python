"""The bracket's played-match codec and its matchday running order."""

import uuid

import pytest

from xkoranate.athlete import XkorAthlete
from xkoranate.competitions.bracketresults import (THIRD_PLACE_ROUND, BracketRows,
                                                   MatchdaySchedule)


def athlete(name):
    a = XkorAthlete()
    a.name = name
    a.id = uuid.uuid4()  # a bare XkorAthlete has none, and rows key on it
    return a


def resolverFor(*athletes):
    byId = {str(a.id): a for a in athletes}
    return lambda id: byId.get(id) if id else None


def test_a_row_round_trips():
    home, away = athlete("Home"), athlete("Away")
    row = BracketRows.make(0, 3, home, away, 2.0, 1.0, "OT", home)
    parsed = BracketRows.parse(row)

    assert parsed["round"] == "0"
    assert parsed["match"] == 3
    assert parsed["home"] == str(home.id)
    assert parsed["away"] == str(away.id)
    assert parsed["score1"] == 2.0 and parsed["score2"] == 1.0
    assert parsed["decider"] == "OT"
    assert parsed["winner"] == str(home.id)


def test_a_bye_row_round_trips():
    home = athlete("Home")
    parsed = BracketRows.parse(BracketRows.make(0, 1, home, None, None, None, "bye", home))
    assert parsed["away"] == ""
    assert parsed["score1"] is None and parsed["score2"] is None


def test_a_malformed_row_is_ignored():
    assert BracketRows.parse("nonsense") is None
    rows = BracketRows(["nonsense"])
    assert rows.forRound(0) == {}


def test_dropping_a_round_leaves_the_others():
    a, b = athlete("A"), athlete("B")
    rows = BracketRows([BracketRows.make(0, 0, a, b, 1.0, 0.0, "", a),
                        BracketRows.make(1, 0, a, b, 1.0, 0.0, "", b)])
    rows.dropRound(0)

    assert rows.forRound(0) == {}
    assert set(rows.forRound(1)) == {0}


def test_winners_are_none_until_the_round_is_complete():
    a, b = athlete("A"), athlete("B")
    resolve = resolverFor(a, b)
    rows = BracketRows([BracketRows.make(0, 0, a, b, 1.0, 0.0, "", a)])

    assert rows.winners(0, 2, resolve) is None  # only one of two matches played
    rows.append(BracketRows.make(0, 1, b, a, 1.0, 0.0, "", b))
    assert [x.name for x in rows.winners(0, 2, resolve)] == ["A", "B"]


def test_losers_are_the_other_side_of_each_match():
    a, b = athlete("A"), athlete("B")
    rows = BracketRows([BracketRows.make(0, 0, a, b, 1.0, 0.0, "", a),
                        BracketRows.make(0, 1, a, b, 0.0, 1.0, "", b)])
    assert [x.name for x in rows.losers(0, resolverFor(a, b))] == ["B", "A"]


def test_a_bye_has_no_loser():
    a = athlete("A")
    rows = BracketRows([BracketRows.make(0, 0, a, None, None, None, "bye", a)])
    assert rows.losers(0, resolverFor(a)) == []


# ------------------------------------------------------------ running order


def test_without_a_playoff_matchdays_are_rounds():
    schedule = MatchdaySchedule(3, False)
    assert len(schedule) == 3
    assert schedule.order == [(0, False), (1, False), (2, False)]
    for md in range(3):
        assert schedule.roundForMatchday(md) == (md, False)
        assert schedule.matchdayForRound(md) == md


def test_the_playoff_sits_before_the_final():
    schedule = MatchdaySchedule(3, True)
    assert len(schedule) == 4
    assert schedule.order == [(0, False), (1, False), (1, True), (2, False)]
    assert schedule.roundForMatchday(2) == (1, True)  # losers of the semi-finals
    assert schedule.roundForMatchday(3) == (2, False)  # the final, pushed back
    assert schedule.matchdayForRound(2) == 3
    assert schedule.thirdPlaceMatchday() == 2


@pytest.mark.parametrize("rounds", [2, 3, 4, 5])
def test_the_mapping_is_its_own_inverse(rounds):
    for thirdPlace in (False, True):
        schedule = MatchdaySchedule(rounds, thirdPlace)
        for round_ in range(rounds):
            md = schedule.matchdayForRound(round_)
            assert schedule.roundForMatchday(md) == (round_, False)


def test_a_playoff_is_not_offered_for_a_one_round_bracket():
    schedule = MatchdaySchedule(1, True)
    assert len(schedule) == 1
    assert schedule.thirdPlaceMatchday() == 1  # one past the end: nowhere


def test_match_numbering_counts_in_playing_order():
    schedule = MatchdaySchedule(3, True)  # 4 + 2 + playoff + 1
    matchesInRound = lambda r: 1 << (3 - 1 - r)

    assert schedule.matchesBefore(0, matchesInRound) == 0  # quarter-finals: 1-4
    assert schedule.matchesBefore(1, matchesInRound) == 4  # semi-finals: 5-6
    assert schedule.matchesBefore(2, matchesInRound) == 6  # playoff: 7
    assert schedule.matchesBefore(3, matchesInRound) == 7  # the final: 8


def test_the_third_place_marker_is_not_a_round_number():
    assert THIRD_PLACE_ROUND == "3P"
    assert BracketRows.parse(
        BracketRows.make(THIRD_PLACE_ROUND, 0, athlete("A"), athlete("B"),
                         1.0, 0.0, "", athlete("A")))["round"] == THIRD_PLACE_ROUND
