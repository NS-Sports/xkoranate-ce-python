from collections import Counter
from itertools import combinations

import pytest

from xkoranate.competitions.conference import (
    conferencePairings, conferenceSchedule, interleave)
from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition

LAYOUTS = [
    [4, 4],
    [4, 3],
    [3, 3, 3],
    [4, 4, 4, 4],
    [3, 3, 3, 3, 3],  # five conferences: the prototype repeated fixtures here
    [5, 2],
    [6, 4, 5],
]
LEGS = [(1, 1), (2, 1), (2, 2), (1, 0), (0, 1)]


def fixtures(schedule):
    for md, day in enumerate(schedule):
        for section in day:
            for home, away in section.fixtures:
                yield md, section, home, away


def teams(sizes):
    return [(c, i) for c, size in enumerate(sizes) for i in range(size)]


@pytest.mark.parametrize("sizes", LAYOUTS)
@pytest.mark.parametrize("own,other", LEGS)
def test_nobody_plays_twice_on_one_matchday(sizes, own, other):
    for day in conferenceSchedule(sizes, own, other):
        seen = Counter(t for s in day for f in s.fixtures for t in f)
        assert max(seen.values()) == 1


@pytest.mark.parametrize("sizes", LAYOUTS)
@pytest.mark.parametrize("own,other", LEGS)
def test_every_pair_meets_the_right_number_of_times(sizes, own, other):
    meetings = Counter(frozenset((h, a)) for _, _, h, a in
                       fixtures(conferenceSchedule(sizes, own, other)))
    for a, b in combinations(teams(sizes), 2):
        expected = own if a[0] == b[0] else other
        assert meetings[frozenset((a, b))] == expected, (a, b)


@pytest.mark.parametrize("sizes", LAYOUTS)
def test_two_legs_give_every_pair_one_home_game_each(sizes):
    home = Counter((h, a) for _, _, h, a in fixtures(conferenceSchedule(sizes, 2, 2)))
    for a, b in combinations(teams(sizes), 2):
        assert home[(a, b)] == 1 and home[(b, a)] == 1, (a, b)


def test_equal_even_conferences_split_cross_games_home_and_away():
    homes, aways = Counter(), Counter()
    for _, section, h, a in fixtures(conferenceSchedule([4, 4, 4, 4], 1, 1)):
        if section.kind == "inter":
            homes[h] += 1
            aways[a] += 1
    for t in teams([4, 4, 4, 4]):
        assert homes[t] == aways[t] == 6


def test_sections_are_labelled_by_the_conferences_playing():
    for _, section, h, a in fixtures(conferenceSchedule([4, 3, 5], 1, 1)):
        if section.kind == "intra":
            assert h[0] == a[0] == section.conferences[0]
        else:
            assert {h[0], a[0]} == set(section.conferences)
            assert h[0] != a[0]


@pytest.mark.parametrize("sizes", LAYOUTS)
def test_cross_matchdays_are_spread_evenly(sizes):
    schedule = conferenceSchedule(sizes, 2, 1)
    cross = [md for md, day in enumerate(schedule) if day[0].kind == "inter"]
    intra = [md for md, day in enumerate(schedule) if day[0].kind == "intra"]
    assert cross and intra
    # whichever kind is rarer never comes twice in a row
    rarer = cross if len(cross) <= len(intra) else intra
    assert all(b - a > 1 for a, b in zip(rarer, rarer[1:]))


def test_matchdays_never_mix_intra_and_cross_play():
    for day in conferenceSchedule([4, 4, 4], 2, 1):
        assert len({s.kind for s in day}) == 1


def test_schedule_is_deterministic():
    assert conferenceSchedule([5, 4, 4], 2, 1) == conferenceSchedule([5, 4, 4], 2, 1)


def test_matchday_count_for_two_conferences_of_four():
    # 3 rounds a leg within, 4 rounds across
    assert len(conferenceSchedule([4, 4], 2, 1)) == 2 * 3 + 4


def test_a_single_conference_schedules_like_a_round_robin():
    schedule = conferenceSchedule([6], 2, 1)
    assert len(schedule) == 10
    for md, day in enumerate(schedule):
        expected = XkorRoundRobinCompetition.generateFixtures(md, 6)
        assert [(h[1], a[1]) for h, a in day[0].fixtures] == expected


def test_empty_conferences_and_zero_legs_schedule_nothing():
    assert conferenceSchedule([], 2, 1) == []
    assert conferenceSchedule([0, 0], 2, 1) == []
    assert conferenceSchedule([4, 4], 0, 0) == []
    assert conferenceSchedule([1, 1, 1], 2, 0) == []


def test_an_empty_conference_is_left_out_of_cross_play():
    schedule = conferenceSchedule([4, 0, 4], 1, 1)
    assert all(1 not in s.conferences for day in schedule for s in day)
    assert len(schedule) == 3 + 4


def test_conference_pairings_meet_each_pair_once():
    for n in range(2, 9):
        rounds = conferencePairings(range(n))
        pairs = [p for r in rounds for p in r]
        assert len(pairs) == len(set(pairs)) == n * (n - 1) // 2
        for r in rounds:
            used = [c for p in r for c in p]
            assert len(used) == len(set(used))


def test_interleave_spreads_the_rarer_kind():
    assert interleave(6, 4) == [False, False, True, False, True,
                                False, False, True, False, True]
    assert interleave(3, 0) == [False] * 3
    assert interleave(0, 2) == [True] * 2
