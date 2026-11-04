import itertools
import random

import pytest

from xkoranate.competitions import qualification
from xkoranate.competitions.qualification import (MODE_OFF, MODE_TOP,
                                                  MODE_TOP_PLUS_BEST,
                                                  QualificationGroup,
                                                  QualificationSettings,
                                                  leagueMarkers, ordinal)
from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition
from xkoranate.competitions.standardcompetition import XkorMassStartCompetition
from xkoranate.startlist import XkorStartListGroup
from xkoranate.athlete import XkorAthlete
from xkoranate.tablegenerator.table import XkorTable
from xkoranate.tablegenerator.tablecolumn import XkorTableColumn

FOOTBALL = [(3, 0), (0, 3), (1, 1)]  # win / loss / draw, home and away


def group(current, remaining=(), outcomes=FOOTBALL, order=None):
    return QualificationGroup(teams=list(current), current=dict(current),
                              remaining=list(remaining), outcomes=outcomes, order=order)


def top(x):
    return QualificationSettings(MODE_TOP, x)


# --- settings ----------------------------------------------------------------

def test_settings_round_trip_through_competition_options():
    s = QualificationSettings(MODE_TOP_PLUS_BEST, 2, 4)
    assert QualificationSettings.fromOptions(s.toOptions()) == s
    assert all(isinstance(v, str) for v in s.toOptions().values())


def test_settings_default_to_off_and_survive_junk():
    assert QualificationSettings.fromOptions({}).mode == MODE_OFF
    assert QualificationSettings.fromOptions({"qualificationMode": "nonsense"}).mode == MODE_OFF
    assert QualificationSettings.fromOptions({"qualificationPlaces": "0"}).places == 1


def test_best_of_needs_more_than_one_group():
    s = QualificationSettings(MODE_TOP_PLUS_BEST, 2, 1)
    assert s.forGroupCount(1).mode == MODE_TOP
    assert s.forGroupCount(3).mode == MODE_TOP_PLUS_BEST


@pytest.mark.parametrize("n,expected", [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"),
                                        (11, "11th"), (12, "12th"), (13, "13th"),
                                        (21, "21st"), (22, "22nd"), (103, "103rd")])
def test_ordinal(n, expected):
    assert ordinal(n) == expected


def test_off_marks_nothing():
    g = group({"A": 9, "B": 0}, order=[["A"], ["B"]])
    assert leagueMarkers([g], QualificationSettings(MODE_OFF, 1)) == [{}]


# --- one group, matches still to play ---------------------------------------

def test_clinch_and_elimination_with_a_round_to_go():
    # A can't be caught by two teams; D can't reach second
    g = group({"A": 6, "B": 4, "C": 1, "D": 0}, [("A", "D"), ("B", "C")])
    assert leagueMarkers([g], top(2)) == [{"A": "Q", "D": "E"}]


def test_a_possible_tie_on_points_counts_against_the_team():
    # B can only be caught by C winning, which leaves them level on 4:
    # the tiebreakers aren't known yet, so no Q for B
    g = group({"A": 6, "B": 4, "C": 1, "D": 0}, [("A", "D"), ("B", "C")])
    assert "B" not in leagueMarkers([g], top(2))[0]
    # and C, who can draw level with B, isn't out either
    assert "C" not in leagueMarkers([g], top(2))[0]


def test_enumeration_sees_that_rivals_who_meet_cant_both_win(monkeypatch):
    # B and C both could reach 5, but they play each other: only one can
    g = group({"A": 4, "B": 2, "C": 2, "D": 2}, [("B", "C")])
    assert leagueMarkers([g], top(2))[0].get("A") == "Q"
    # judged team by team (too many scenarios), it's left open — never wrong
    monkeypatch.setattr(qualification, "SCENARIO_CAP", 0)
    assert "A" not in leagueMarkers([g], top(2))[0]


def test_no_draws_with_shootout_points():
    # NHL-style: 2 for any win, 1 for an overtime/shootout loss, no draws
    nhl = [(2, 0), (0, 2), (2, 1), (1, 2)]
    g = group({"A": 5, "B": 3, "C": 3}, [("B", "C")], outcomes=nhl)
    # the winner reaches 5 at most, level with A: A not yet clear
    assert leagueMarkers([g], top(1))[0] == {}
    g = group({"A": 6, "B": 3, "C": 3}, [("B", "C")], outcomes=nhl)
    assert leagueMarkers([g], top(1))[0] == {"A": "Q", "B": "E", "C": "E"}


def test_unknown_metric_marks_nothing_until_complete():
    g = QualificationGroup(teams=["A", "B"], current=None, remaining=[("A", "B")], outcomes=None)
    assert leagueMarkers([g], top(1)) == [{}]


# --- complete groups ---------------------------------------------------------

def test_complete_group_uses_the_real_order():
    g = group({"A": 9, "B": 4, "C": 4, "D": 0}, order=[["A"], ["B"], ["C"], ["D"]])
    assert leagueMarkers([g], top(2)) == [{"A": "Q", "B": "Q", "C": "E", "D": "E"}]


def test_a_tie_straddling_the_cut_is_left_open():
    g = group({"A": 9, "B": 4, "C": 4, "D": 0}, order=[["A"], ["B", "C"], ["D"]])
    assert leagueMarkers([g], top(2)) == [{"A": "Q", "D": "E"}]
    # but a tie entirely inside (or outside) the places is decided
    assert leagueMarkers([g], top(3)) == [{"A": "Q", "B": "Q", "C": "Q", "D": "E"}]


# --- top X in each group + best N next-placed -------------------------------

def completeGroup(prefix, points):
    names = ["%s%d" % (prefix, i + 1) for i in range(len(points))]
    return group(dict(zip(names, points)), order=[[n] for n in names])


def test_best_third_placed_from_the_exact_ranking():
    groups = [completeGroup("A", [9, 6, 4, 0]), completeGroup("B", [9, 6, 3, 0]),
              completeGroup("C", [9, 6, 5, 0])]
    ranked = []

    def crossRank(candidates):
        ranked.extend(candidates)
        return [[(2, "C3")], [(0, "A3")], [(1, "B3")]]

    markers = leagueMarkers(groups, QualificationSettings(MODE_TOP_PLUS_BEST, 2, 1), crossRank)
    assert sorted(ranked) == [(0, "A3"), (1, "B3"), (2, "C3")]
    assert markers[2]["C3"] == "Q"
    assert markers[0]["A3"] == "E" and markers[1]["B3"] == "E"
    assert all(markers[i]["%s1" % p] == "Q" and markers[i]["%s4" % p] == "E"
               for i, p in enumerate("ABC"))


def test_a_tie_at_the_best_of_cut_is_left_open():
    groups = [completeGroup("A", [9, 6, 4, 0]), completeGroup("B", [9, 6, 4, 0]),
              completeGroup("C", [9, 6, 3, 0])]
    markers = leagueMarkers(groups, QualificationSettings(MODE_TOP_PLUS_BEST, 2, 1),
                            lambda c: [[(0, "A3"), (1, "B3")], [(2, "C3")]])
    assert "A3" not in markers[0] and "B3" not in markers[1]
    assert markers[2]["C3"] == "E"


def test_best_of_judged_on_points_while_a_group_is_still_playing():
    done = completeGroup("A", [9, 8, 7, 0])
    # whoever finishes third in B ends on 6 points at most, short of A3's 7
    playing = group({"B1": 9, "B2": 7, "B3": 3, "B4": 1}, [("B3", "B4")])
    markers = leagueMarkers([done, playing], QualificationSettings(MODE_TOP_PLUS_BEST, 2, 1))
    assert markers[0] == {"A1": "Q", "A2": "Q", "A3": "Q", "A4": "E"}
    assert markers[1] == {"B1": "Q", "B2": "Q", "B3": "E", "B4": "E"}


# --- soundness: brute force every completion ---------------------------------

def completions(g):
    for results in itertools.product(g.outcomes, repeat=len(g.remaining)):
        final = {t: g.current.get(t, 0) for t in g.teams}
        for (home, away), (dh, da) in zip(g.remaining, results):
            final[home] += dh
            final[away] += da
        yield final


def randomGroup(rng, prefix, size, played):
    names = ["%s%d" % (prefix, i) for i in range(size)]
    pairs = [p for p in itertools.combinations(names, 2)]
    rng.shuffle(pairs)
    return group({n: rng.choice([0, 1, 3, 4, 6]) for n in names}, pairs[:played])


@pytest.mark.parametrize("cap", [qualification.SCENARIO_CAP, 0])
def test_top_markers_hold_in_every_completion(monkeypatch, cap):
    monkeypatch.setattr(qualification, "SCENARIO_CAP", cap)
    rng = random.Random(1093)
    for _ in range(150):
        g = randomGroup(rng, "T", rng.choice([3, 4, 5]), rng.randint(1, 5))
        x = rng.randint(1, len(g.teams) - 1)
        markers = leagueMarkers([g], top(x))[0]
        for final in completions(g):
            for team, marker in markers.items():
                ahead = sum(1 for o, v in final.items() if o != team and v > final[team])
                levelOrAhead = sum(1 for o, v in final.items() if o != team and v >= final[team])
                if marker == "Q":
                    assert levelOrAhead < x, (g, x, final, team)
                else:
                    assert ahead >= x, (g, x, final, team)


@pytest.mark.parametrize("cap", [qualification.SCENARIO_CAP, 0])
def test_best_of_markers_hold_in_every_completion(monkeypatch, cap):
    monkeypatch.setattr(qualification, "SCENARIO_CAP", cap)
    rng = random.Random(36)
    x = 1
    for _ in range(60):
        groups = [randomGroup(rng, p, 3, rng.randint(0, 2)) for p in "ABC"]
        n = rng.randint(1, 2)
        markers = leagueMarkers(groups, QualificationSettings(MODE_TOP_PLUS_BEST, x, n))
        for finals in itertools.product(*[list(completions(g)) for g in groups]):
            nextValues = [sorted(f.values(), reverse=True)[x] for f in finals]
            for groupNo, (final, m) in enumerate(zip(finals, markers)):
                others = [v for h, v in enumerate(nextValues) if h != groupNo]
                for team, marker in m.items():
                    v = final[team]
                    ahead = sum(1 for o, w in final.items() if o != team and w > v)
                    levelOrAhead = sum(1 for o, w in final.items() if o != team and w >= v)
                    if marker == "Q":
                        # top x even losing every tie, or next-placed and
                        # clear of enough of the other groups' next-placed
                        assert levelOrAhead < x or (
                            levelOrAhead == x and sum(1 for w in others if w >= v) < n)
                    else:
                        assert ahead >= x and (
                            ahead > x or sum(1 for w in others if w > v) >= n)


# --- the table's marker column -----------------------------------------------

def test_marker_column_has_a_blank_heading_and_sits_after_the_points():
    t = XkorTable()
    t.setColumns([XkorTableColumn("position", "", 1), XkorTableColumn("name", "Group A", 10),
                  XkorTableColumn("points", "Pts", 4)])
    t.setSortCriteria(["points"])
    t.setPointsForWin(3)
    t.insertMatch("Aquilla", "Busby", 2, 0)
    t.generate()
    plain = t.toText()

    t.setColumns(XkorRoundRobinCompetition._withQualificationColumn(t.getColumns()))
    t.setMarkers({"Aquilla": "Q", "Busby": "E"})
    lines = t.toText().split("\n")
    assert lines[0] == plain.split("\n")[0] + "  "
    assert lines[1] == plain.split("\n")[1] + " Q"
    assert lines[2] == plain.split("\n")[2] + " E"


def test_marker_column_goes_before_a_results_grid():
    cols = [XkorTableColumn("position"), XkorTableColumn("name"), XkorTableColumn("points"),
            XkorTableColumn("resultsGrid")]
    types = [c.columnType for c in XkorRoundRobinCompetition._withQualificationColumn(cols)]
    assert types == ["position", "name", "points", "qualification", "resultsGrid"]


def test_a_table_without_the_column_is_unchanged_by_markers():
    t = XkorTable()
    t.setColumns([XkorTableColumn("position", "", 1), XkorTableColumn("name", "G", 10)])
    t.insertMatch("Aquilla", "Busby", 1, 0)
    t.generate()
    before = t.toText()
    t.setMarkers({"Aquilla": "Q"})
    assert t.toText() == before


# --- mass start heats -----------------------------------------------------------

def massStart(heatSizes, heatRanks=None):
    c = XkorMassStartCompetition()
    c.startList.groups = [XkorStartListGroup("Heat %d" % (i + 1), [XkorAthlete() for _ in range(n)])
                          for i, n in enumerate(heatSizes)]
    c.userOpt = {} if heatRanks is None else {"heatRanks": heatRanks}
    return c


HEATS = """  Heat 1
1 Ann     10.10
2 Bea     10.20
3 Cat     10.30
— Dot       DNF

  Heat 2
1 Eve     10.05
2 Fay     10.15
  Gus     10.15
— Hal       DSQ

"""


def test_heat_markers_follow_the_ranks():
    lines = massStart([4, 4]).formatQualifications(HEATS, 0, top(2)).split("\n")
    assert [line[-1] for line in lines[1:5]] == ["Q", "Q", "E", "E"]  # DNF is out
    # markers line up in one column, the header untouched
    assert len({len(line) for line in lines[1:5]}) == 1
    assert lines[0] == "  Heat 1"
    assert lines[7].endswith(" Q") and lines[10].endswith(" E")


def test_heat_tie_straddling_the_cut_is_left_open():
    # Fay and Gus share second: with two places that's 2nd–3rd, so open…
    lines = massStart([4, 4]).formatQualifications(HEATS, 0, top(2)).split("\n")
    assert lines[8] == "2 Fay     10.15" and lines[9] == "  Gus     10.15"
    # …and with three places, both are in
    lines = massStart([4, 4]).formatQualifications(HEATS, 0, top(3)).split("\n")
    assert lines[8].endswith(" Q") and lines[9].endswith(" Q")


def test_best_next_placed_heat_finisher_from_saved_ranks():
    # overall ranks, per heat in line order: Bea 4th overall, Fay/Gus 3rd
    ranks = [["2", "4", "6", ""], ["1", "3", "3", ""]]
    s = QualificationSettings(MODE_TOP_PLUS_BEST, 1, 1)
    lines = massStart([4, 4], ranks).formatQualifications(HEATS, 0, s).split("\n")
    assert lines[1].endswith(" Q") and lines[7].endswith(" Q")  # heat winners
    assert lines[2].endswith(" E")  # Bea is beaten by heat 2's runner-up
    assert lines[3].endswith(" E")
    # which of Fay and Gus is heat 2's runner-up is a tie: open
    assert lines[8] == "2 Fay     10.15" and lines[9] == "  Gus     10.15"


def test_best_next_placed_needs_saved_ranks():
    s = QualificationSettings(MODE_TOP_PLUS_BEST, 1, 1)
    lines = massStart([4, 4]).formatQualifications(HEATS, 0, s).split("\n")
    assert lines[1].endswith(" Q") and lines[3].endswith(" E")
    assert lines[2] == "2 Bea     10.20"  # can't compare her with heat 2 unaided


def test_unrecognised_heat_text_is_left_alone():
    assert massStart([4, 4]).formatQualifications("something else\n", 0, top(1)) == "something else\n"


def test_unsorted_mass_start_has_nothing_to_mark():
    c = massStart([4])
    c.userOpt = {"sortResults": "false"}
    assert not c.supportsQualifications()
    assert c.formatQualifications(HEATS, 0, top(1)) == HEATS


# --- conferences: games against other groups, with their own points --------

def test_a_game_against_another_conference_counts_for_one_side_only():
    # A's last game is against an outsider worth 2 a win; B's is in-conference
    crossWin = [(2, 0), (0, 2), (1, 1)]
    g = QualificationGroup(teams=["A", "B", "C"], current={"A": 6, "B": 3, "C": 3},
                           remaining=[("A", "Z9", crossWin), ("B", "C")], outcomes=FOOTBALL)
    # B or C can reach 6 at most: level with A, so A isn't clear of both
    assert leagueMarkers([g], top(1))[0] == {}
    g.current["A"] = 7
    assert leagueMarkers([g], top(1))[0] == {"A": "Q", "B": "E", "C": "E"}


def conferenceCompletions(groups, fixtures):
    """Every outcome of the shared fixture list, as one final dict per group."""
    for results in itertools.product(*[o for _h, _a, o in fixtures]):
        totals = {t: v for g in groups for t, v in g.current.items()}
        for (home, away, _o), (dh, da) in zip(fixtures, results):
            totals[home] += dh
            totals[away] += da
        yield [{t: totals[t] for t in g.teams} for g in groups]


@pytest.mark.parametrize("cap", [qualification.SCENARIO_CAP, 0])
def test_conference_markers_hold_in_every_completion(monkeypatch, cap):
    monkeypatch.setattr(qualification, "SCENARIO_CAP", cap)
    rng = random.Random(24)
    crossOutcomes = [(2, 0), (0, 2), (1, 1)]
    for _ in range(40):
        confs = [["%s%d" % (p, i) for i in range(3)] for p in "AB"]
        everyone = confs[0] + confs[1]
        pairs = list(itertools.combinations(everyone, 2))
        rng.shuffle(pairs)
        fixtures = [(h, a, crossOutcomes if h[0] != a[0] else FOOTBALL)
                    for h, a in pairs[:rng.randint(1, 5)]]
        groups = [QualificationGroup(
            teams=c, current={t: rng.choice([0, 1, 3, 4, 6]) for t in c},
            remaining=[f for f in fixtures if f[0] in c or f[1] in c], outcomes=FOOTBALL)
            for c in confs]
        settings = QualificationSettings(MODE_TOP_PLUS_BEST, 1, 1)
        markers = leagueMarkers(groups, settings)
        for finals in conferenceCompletions(groups, fixtures):
            nextValues = [sorted(f.values(), reverse=True)[1] for f in finals]
            for groupNo, (final, m) in enumerate(zip(finals, markers)):
                other = nextValues[1 - groupNo]
                for team, marker in m.items():
                    v = final[team]
                    ahead = sum(1 for o, w in final.items() if o != team and w > v)
                    levelOrAhead = sum(1 for o, w in final.items() if o != team and w >= v)
                    if marker == "Q":
                        assert levelOrAhead < 1 or (levelOrAhead == 1 and other < v)
                    else:
                        assert ahead >= 1 and (ahead > 1 or other > v)
