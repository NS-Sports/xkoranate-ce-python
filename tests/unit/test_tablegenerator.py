import functools
import os
import re
import subprocess
import sys

import pytest
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QApplication

from xkoranate.tablegenerator.decider import (MATCH_RESULT_PATTERN, classify,
                                              stripTrailingDeciders)
from xkoranate.tablegenerator.table import XkorTable
from xkoranate.tablegenerator.tablematch import XkorTableMatch
from xkoranate.tablegenerator.tablerow import XkorTableRow
from xkoranate.tablegenerator.tablesorter import XkorTableSorter
from xkoranate.xml.xmltablereader import XkorXmlTableReader
from xkoranate.xml.xmltablewriter import XkorXmlTableWriter

def _parse_manual_line(line):
    """Mirror XkorTableGenerator.generateMatches()'s per-line parsing
    without needing a QApplication to instantiate the widget itself."""
    from xkoranate.tablegenerator.tablegenerator import _qLeft, _qRight
    from xkoranate.variant import toDouble

    rx = QRegularExpression(MATCH_RESULT_PATTERN)
    match = rx.match(line)
    if not match.hasMatch():
        return None
    index = match.capturedStart(0)
    matchedLength = match.capturedLength(0)
    homeTeam = _qLeft(line, index - 1)
    awayTeam = _qRight(line, len(line) - index - matchedLength - 1)
    homeScore = toDouble(match.captured(1))
    awayScore = toDouble(match.captured(2))
    decider = match.captured(3) or None
    awayTeam, otherScore1, otherScore2, otherDecider = stripTrailingDeciders(
        awayTeam, homeScore, awayScore)
    if otherDecider is not None:
        decider = otherDecider
        homeScore, awayScore = otherScore1, otherScore2
    return (homeTeam, awayTeam, homeScore, awayScore, decider)


def _row_with_matches(*matches):
    """Build an XkorTableRow named "Home" from a sequence of
    (opponentScore, ownScore, home, decider) tuples, mirroring how
    XkorTable.addMatchToData() drives XkorTableRow.insertMatch()."""
    row = XkorTableRow("Home")
    for opponentScore, ownScore, home, decider in matches:
        row.insertMatch("Away", ownScore, opponentScore, home, decider)
    return row


def test_regulation_win_loss_unaffected_by_decider_fields():
    row = _row_with_matches((1, 3, True, None), (0, 2, True, None))
    assert row.wins() == 2
    assert row.otWins() == 0
    assert row.soWins() == 0
    assert row.regulationWins() == 2
    assert row.losses() == 0


def test_ot_and_so_wins_are_tracked_separately_from_regulation():
    row = _row_with_matches(
        (1, 3, True, None),   # regulation win
        (2, 3, True, "OT"),   # OT win
        (0, 1, True, "SO"),   # SO win
        (3, 1, True, "OT"),   # OT loss
        (2, 0, True, "SO"),   # SO loss
    )
    assert row.wins() == 3
    assert row.otWins() == 1
    assert row.soWins() == 1
    assert row.regulationWins() == 1
    assert row.losses() == 2
    assert row.otLosses() == 1
    assert row.soLosses() == 1
    assert row.regulationLosses() == 0


def test_getPoints_matches_old_formula_when_no_deciders_are_used():
    row = _row_with_matches((1, 3, True, None), (1, 1, True, None), (3, 0, True, None))
    t = XkorTable()
    t.setPointsForWin(3)
    t.setPointsForDraw(1)
    t.setPointsForLoss(0)
    # the old formula: wins*pointsForWin + draws*pointsForDraw + losses*pointsForLoss
    assert t.getPoints(row) == row.wins() * 3 + row.draws() * 1 + row.losses() * 0


def test_getPoints_supports_nhl_style_scoring():
    row = _row_with_matches(
        (1, 3, True, None),   # regulation win: 2 pts
        (2, 3, True, "OT"),   # OT win: 2 pts
        (1, 2, True, "SO"),   # SO win: 2 pts
        (3, 2, True, "OT"),   # OT loss: 1 pt
        (2, 1, True, "SO"),   # SO loss: 1 pt
        (3, 0, True, None),   # regulation loss: 0 pts
    )
    t = XkorTable()
    t.setPointsForWin(2)
    t.setPointsForDraw(2)
    t.setPointsForLoss(0)
    t.setPointsForOTWin(2)
    t.setPointsForSOWin(2)
    t.setPointsForOTLoss(1)
    t.setPointsForSOLoss(1)
    # 3 wins (all worth 2) + 1 OT loss (1) + 1 SO loss (1) + 1 regulation loss (0)
    assert t.getPoints(row) == 3 * 2 + 1 + 1 + 0


def test_ot_so_points_fall_back_to_win_loss_when_unset():
    row = _row_with_matches((1, 3, True, "OT"), (3, 1, True, "SO"))
    t = XkorTable()
    t.setPointsForWin(3)
    t.setPointsForLoss(0)
    assert t.getPointsForOTWin() == 3
    assert t.getPointsForSOLoss() == 0
    assert t.getPoints(row) == 3  # 1 OT win (3) + 1 SO loss (0)


def test_regulationWins_and_otWins_sort_criteria():
    a = _row_with_matches((0, 2, True, None))  # regulation win
    b = _row_with_matches((1, 2, True, "OT"))  # OT win
    c = _row_with_matches((1, 2, True, "SO"))  # SO win

    sorter = XkorTableSorter()

    ordered = sorter.sort([a, b, c], "regulationWins")
    assert ordered[0] == [a]
    assert set(id(x) for x in ordered[1]) == {id(b), id(c)}

    # a has no OT/SO wins, so it ranks below the tied b/c pair here
    ordered = sorter.sort([a, b, c], "otWins")
    assert set(id(x) for x in ordered[0]) == {id(b), id(c)}
    assert ordered[1] == [a]


def test_points_sort_criterion_respects_ot_so_overrides():
    # NHL-style: OT/SO wins are worth the same as a regulation win (2pts each),
    # but an OT/SO loss (1pt) still outranks a regulation loss (0pts)
    winner = _row_with_matches((1, 2, True, "SO"))       # 1 SO win
    loserWithOTLoss = _row_with_matches((3, 2, True, "OT"))  # 1 OT loss
    loserOutright = _row_with_matches((3, 0, True, None))    # 1 regulation loss

    sorter = XkorTableSorter()
    sorter.setPointsForWin(2)
    sorter.setPointsForDraw(2)
    sorter.setPointsForLoss(0)
    sorter.setPointsForOTLoss(1)
    sorter.setPointsForSOLoss(1)

    ordered = sorter.sort([loserOutright, winner, loserWithOTLoss], "points")
    assert ordered == [[winner], [loserWithOTLoss], [loserOutright]]


def test_manual_entry_pattern_recognizes_optional_decider():
    rx = QRegularExpression(MATCH_RESULT_PATTERN)

    m = rx.match("Aquilla 3–2 Busby")
    assert m.hasMatch()
    assert m.captured(3) == ""

    m = rx.match("Aquilla 3–2 OT Busby")
    assert m.hasMatch()
    assert m.captured(1) == "3"
    assert m.captured(2) == "2"
    assert m.captured(3) == "OT"

    m = rx.match("Aquilla 1–4 SO Busby")
    assert m.hasMatch()
    assert m.captured(3) == "SO"


def test_xml_readMatches_pattern_recognizes_optional_decider():
    rx = re.compile(MATCH_RESULT_PATTERN)

    m = rx.search("Aquilla 3–2 Busby")
    assert m.group(3) is None

    m = rx.search("Aquilla 3–2 OT Busby")
    assert m.group(3) == "OT"


def test_xml_round_trip_preserves_decider_and_ot_so_points(tmp_path):
    filename = os.path.join(str(tmp_path), "table.xml")

    t = XkorTable()
    t.setColumns([])
    t.setPointsForWin(2)
    t.setPointsForDraw(2)
    t.setPointsForLoss(0)
    t.setPointsForOTWin(2)
    t.setPointsForSOWin(2)
    t.setPointsForOTLoss(1)
    t.setPointsForSOLoss(1)
    t.setShowOvertime(True)
    t.setMatches([
        XkorTableMatch("Aquilla", "Busby", 3, 2, "OT"),
        XkorTableMatch("Busby", "Aquilla", 1, 4, "SO"),
    ])

    XkorXmlTableWriter(filename, t)

    reader = XkorXmlTableReader(filename)
    assert not reader.hasError()
    t2 = reader.table()

    matches = t2.getMatches()
    assert [(m.team1, m.team2, m.score1, m.score2, m.decider) for m in matches] == [
        ("Aquilla", "Busby", 3.0, 2.0, "OT"),
        ("Busby", "Aquilla", 1.0, 4.0, "SO"),
    ]

    assert t2.getPointsForOTWin() == 2
    assert t2.getPointsForSOLoss() == 1
    assert t2.getShowOvertime() is True

    row = t2.findTeam("Aquilla")
    assert row.otWins() == 1
    assert row.soWins() == 1
    assert t2.getPoints(row) == 4  # 1 OT win (2) + 1 SO win (2)


def test_xml_reader_falls_back_on_older_files_without_ot_so_fields(tmp_path):
    filename = os.path.join(str(tmp_path), "old_table.xml")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0"?>
<table version="0.3">
 <sortCriteria>
  <sortCriterion>points</sortCriterion>
 </sortCriteria>
 <pointsForWin>3</pointsForWin>
 <pointsForDraw>1</pointsForDraw>
 <pointsForLoss>0</pointsForLoss>
 <columnWidth>2</columnWidth>
 <showDraws>true</showDraws>
 <showResultsGrid>false</showResultsGrid>
 <goalName>G</goalName>
 <matches>
  <match>Aquilla 3–2 Busby</match>
  <match>Busby 1–4 Aquilla</match>
 </matches>
</table>
""")

    reader = XkorXmlTableReader(filename)
    assert not reader.hasError()
    t = reader.table()

    assert t.getPointsForOTWin() == 3  # falls back to pointsForWin
    assert t.getPointsForSOLoss() == 0  # falls back to pointsForLoss
    assert t.getShowOvertime() is False


def test_saving_a_table_that_overrides_nothing_keeps_the_ot_so_fallback(tmp_path):
    # writing out the resolved value would pin it: the reloaded table would
    # then keep 3-point OT wins even after pointsForWin changed
    filename = os.path.join(str(tmp_path), "no_overrides.xml")

    t = XkorTable()
    t.setColumns([])
    t.setPointsForWin(3)
    t.setPointsForDraw(1)
    t.setPointsForLoss(0)

    XkorXmlTableWriter(filename, t)
    with open(filename, encoding="utf-8") as f:
        assert "pointsForOTWin" not in f.read()

    reloaded = XkorXmlTableReader(filename).table()
    assert reloaded.getRawPointsForOTWin() is None
    reloaded.setPointsForWin(2)
    assert reloaded.getPointsForOTWin() == 2


def test_saving_a_table_that_does_override_ot_points_keeps_the_override(tmp_path):
    filename = os.path.join(str(tmp_path), "overrides.xml")

    t = XkorTable()
    t.setColumns([])
    t.setPointsForWin(2)
    t.setPointsForLoss(0)
    t.setPointsForOTLoss(1)

    XkorXmlTableWriter(filename, t)

    reloaded = XkorXmlTableReader(filename).table()
    assert reloaded.getRawPointsForOTLoss() == 1
    reloaded.setPointsForLoss(0)
    assert reloaded.getPointsForOTLoss() == 1  # still overridden, not 0


def test_classify_recognizes_shootout_style_names_regardless_of_case_or_punctuation():
    assert classify("SO") == "SO"
    assert classify("so") == "SO"
    assert classify("shootout") == "SO"
    assert classify("pen.") == "SO"
    assert classify("Penalties") == "SO"
    assert classify("PK") == "SO"


def test_classify_recognizes_every_tiebreaker_name_the_sport_files_use():
    # the full set of <list type="tiebreakerNames"> values across sports/
    assert classify("OT") == "OT"
    assert classify("AET") == "OT"
    assert classify("ET") == "OT"
    assert classify("GG") == "OT"
    assert classify("Sudden Death") == "OT"
    assert classify("+") == "OT"
    assert classify("2OT") == "OT"  # numbered overtime periods


def test_classify_rejects_names_it_doesnt_recognize():
    # nothing in the text distinguishes an unknown tiebreaker name from an
    # ordinary parenthesised suffix on a team name, so we don't guess
    assert classify("Reserve") is None
    assert classify("B") is None
    assert classify("") is None


def test_strip_trailing_deciders_leaves_plain_text_untouched():
    assert stripTrailingDeciders("Busby") == ("Busby", None, None, None)


def test_strip_trailing_deciders_leaves_an_unrecognized_bracketed_suffix_alone():
    # a team name can legitimately end in "(2–1 Something)" — treating it as a
    # decider would invent an OT win and overwrite the real score
    assert stripTrailingDeciders("Busby (2–1 Reserve)", 3, 0) == (
        "Busby (2–1 Reserve)", None, None, None)


def test_manual_entry_keeps_team_names_that_merely_start_with_ot_or_so():
    assert _parse_manual_line("Aquilla 3–2 OTtawa") == ("Aquilla", "OTtawa", 3.0, 2.0, None)
    assert _parse_manual_line("Aquilla 3–2 SOuthampton") == (
        "Aquilla", "SOuthampton", 3.0, 2.0, None)


def test_strip_trailing_deciders_ot_tag_gives_its_own_combined_score():
    assert stripTrailingDeciders("Busby (3–2 OT)", 2, 2) == ("Busby", 3.0, 2.0, "OT")


def test_strip_trailing_deciders_so_only_tag_nudges_the_tied_base_score_towards_the_winner():
    # a shootout's own tally isn't a real score, but a shootout always
    # produces a winner — it must not be recorded as a draw
    assert stripTrailingDeciders("Busby (1–0 SO)", 2, 2) == ("Busby", 3, 2, "SO")
    assert stripTrailingDeciders("Busby (0–1 SO)", 2, 2) == ("Busby", 2, 3, "SO")


def test_strip_trailing_deciders_two_stage_tiebreaker_nudges_from_the_ot_stage_score():
    # OT is played first (still tied, so its "combined" score doesn't move),
    # then a shootout actually decides it — the table score should be the OT
    # stage's score nudged towards the shootout winner, and the decider
    # should reflect the shootout that actually resolved it
    assert stripTrailingDeciders("Busby (2–2 OT) (1–0 SO)", 2, 2) == ("Busby", 3.0, 2.0, "SO")


def test_strip_trailing_deciders_recognizes_sport_specific_names():
    # football-style extra time + penalties, as used by e.g. football_sqis.xml
    assert stripTrailingDeciders("Dorset (2–2 AET) (3–4 pen.)", 2, 2) == ("Dorset", 2.0, 3.0, "SO")
    # netball/korfball/football_grsl-style names that aren't shootouts at all
    assert stripTrailingDeciders("Dorset (3–2 Sudden Death)", 2, 2) == ("Dorset", 3.0, 2.0, "OT")


def test_manual_entry_recognizes_the_simulator_own_output_format():
    # this is what XkorAbstractH2HParadigm._formatScoreResults() actually
    # prints for a simulated hockey match, e.g. copy-pasted from an event's
    # results log straight into the table generator
    assert _parse_manual_line("Aquilla 2–2 Busby (3–2 OT)") == ("Aquilla", "Busby", 3.0, 2.0, "OT")
    assert _parse_manual_line("Aquilla 2–2 Busby (1–0 SO)") == ("Aquilla", "Busby", 3.0, 2.0, "SO")
    assert _parse_manual_line("Charlie 2–2 Dorset (2–2 AET) (3–4 pen.)") == (
        "Charlie", "Dorset", 2.0, 3.0, "SO")


def test_manual_entry_still_recognizes_the_original_inline_marker():
    assert _parse_manual_line("Aquilla 3–2 OT Busby") == ("Aquilla", "Busby", 3.0, 2.0, "OT")
    assert _parse_manual_line("Aquilla 1–4 SO Busby") == ("Aquilla", "Busby", 1.0, 4.0, "SO")


def test_manual_entry_unaffected_when_theres_no_decider_at_all():
    assert _parse_manual_line("Aquilla 3–1 Busby") == ("Aquilla", "Busby", 3.0, 1.0, None)


def test_xml_round_trip_recognizes_simulator_output_format(tmp_path):
    filename = os.path.join(str(tmp_path), "sim_output_table.xml")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0"?>
<table version="0.3">
 <sortCriteria>
  <sortCriterion>points</sortCriterion>
 </sortCriteria>
 <pointsForWin>2</pointsForWin>
 <pointsForDraw>2</pointsForDraw>
 <pointsForLoss>0</pointsForLoss>
 <pointsForOTLoss>1</pointsForOTLoss>
 <pointsForSOLoss>1</pointsForSOLoss>
 <columnWidth>2</columnWidth>
 <showDraws>true</showDraws>
 <showResultsGrid>false</showResultsGrid>
 <goalName>G</goalName>
 <matches>
  <match>Aquilla 2–2 Busby (3–2 OT)</match>
  <match>Busby 2–2 Aquilla (1–0 SO)</match>
 </matches>
</table>
""")

    reader = XkorXmlTableReader(filename)
    assert not reader.hasError()
    t = reader.table()

    matches = t.getMatches()
    assert [(m.team1, m.team2, m.score1, m.score2, m.decider) for m in matches] == [
        ("Aquilla", "Busby", 3.0, 2.0, "OT"),
        # Busby won the shootout (1–0), so it's nudged to a 3–2 win here too —
        # never a recorded draw, since a shootout always has a winner
        ("Busby", "Aquilla", 3.0, 2.0, "SO"),
    ]

    row = t.findTeam("Aquilla")
    assert row.wins() == 1  # the OT win over Busby
    assert row.otWins() == 1
    assert row.losses() == 1  # lost the return leg's shootout
    assert row.soLosses() == 1
    assert t.getPoints(row) == 2 + 1  # 1 OT win (2) + 1 SO loss (1)


def test_home_away_split_stats_from_issue_40_tiebreaker_list():
    # XkorTableRow.insertMatch(opponent, ownScore, opponentScore, home)
    row = XkorTableRow("Home")
    row.insertMatch("Away", 3, 1, True)   # home win, conceded 1 at home
    row.insertMatch("Away", 0, 2, True)   # home loss, conceded 2 at home
    row.insertMatch("Away", 4, 1, False)  # away win

    assert row.losses() == 1
    assert row.homeLosses() == 1
    assert row.homeGoalsAgainst() == 3  # 1 (won) + 2 (lost) — every home game counts
    assert row.awayWins() == 1
    assert row.wins() == 2


def test_losses_home_losses_away_wins_home_goals_against_sort_criteria():
    fewerLosses = XkorTableRow("FewerLosses")
    fewerLosses.insertMatch("X", 3, 1, True)  # home win

    moreLosses = XkorTableRow("MoreLosses")
    moreLosses.insertMatch("X", 1, 3, True)  # home loss, conceded 3 at home
    moreLosses.insertMatch("X", 1, 0, False)  # away win (not a home loss)

    sorter = XkorTableSorter()

    assert sorter.sort([fewerLosses, moreLosses], "losses") == [[fewerLosses], [moreLosses]]
    assert sorter.sort([fewerLosses, moreLosses], "homeLosses") == [[fewerLosses], [moreLosses]]
    assert sorter.sort([fewerLosses, moreLosses], "homeGoalsAgainst") == [[fewerLosses], [moreLosses]]

    awayWinner = XkorTableRow("AwayWinner")
    awayWinner.insertMatch("X", 2, 1, False)  # away win

    noAwayWins = XkorTableRow("NoAwayWins")
    noAwayWins.insertMatch("X", 2, 1, True)  # home win only

    assert sorter.sort([awayWinner, noAwayWins], "awayWins") == [[awayWinner], [noAwayWins]]


def _coin_flip_order(sorter, rows):
    return [row.name() for bin in sorter.sort(rows, "coinFlip") for row in bin]


def test_coin_flip_gives_a_valid_total_order():
    a = XkorTableRow("Aquilla")
    b = XkorTableRow("Busby")
    c = XkorTableRow("Charlie")
    sorter = XkorTableSorter()
    order = _coin_flip_order(sorter, [a, b, c])
    assert sorted(order) == ["Aquilla", "Busby", "Charlie"]


def test_coin_flip_result_sticks_once_made_instead_of_rerolling():
    # once a team's flip is recorded, regenerating the table must not
    # reshuffle it — a coin toss isn't redone just because someone looked at
    # the standings again
    a = XkorTableRow("Aquilla")
    b = XkorTableRow("Busby")
    c = XkorTableRow("Charlie")
    sorter = XkorTableSorter()

    firstOrder = _coin_flip_order(sorter, [a, b, c])
    for _ in range(10):
        assert _coin_flip_order(sorter, [a, b, c]) == firstOrder
        assert _coin_flip_order(sorter, [c, b, a]) == firstOrder  # order of input doesn't matter either


def test_coin_flip_only_assigns_new_teams_not_already_flipped():
    a = XkorTableRow("Aquilla")
    b = XkorTableRow("Busby")
    sorter = XkorTableSorter()
    sorter.sort([a, b], "coinFlip")
    existingFlips = dict(sorter.getCoinFlips())

    # a third team joins the tie later (e.g. a new match added a new team) —
    # the existing two teams' flips must not change
    c = XkorTableRow("Charlie")
    sorter.sort([a, b, c], "coinFlip")
    assert sorter.getCoinFlips()["Aquilla"] == existingFlips["Aquilla"]
    assert sorter.getCoinFlips()["Busby"] == existingFlips["Busby"]
    assert "Charlie" in sorter.getCoinFlips()


def test_coin_flip_result_survives_an_xml_save_and_reload(tmp_path):
    filename = os.path.join(str(tmp_path), "coin_flip_table.xml")

    t = XkorTable()
    t.setColumns([])
    t.setPointsForWin(3)
    t.setPointsForDraw(1)
    t.setPointsForLoss(0)
    t.setSortCriteria(["points", "coinFlip"])
    t.setMatches([
        XkorTableMatch("Aquilla", "Busby", 1, 1),
        XkorTableMatch("Busby", "Aquilla", 1, 1),
    ])
    t.generate()
    originalOrder = [row[0].name() for row in t.data]
    assert sorted(originalOrder) == ["Aquilla", "Busby"]  # tied on everything but the coin flip

    XkorXmlTableWriter(filename, t)

    reader = XkorXmlTableReader(filename)
    assert not reader.hasError()
    reloaded = reader.table()
    reloaded.generate()

    assert [row[0].name() for row in reloaded.data] == originalOrder


@functools.lru_cache(maxsize=None)
def _canCreateQApplication():
    """Whether a QApplication can be constructed here at all.

    Qt aborts the process outright when no platform plugin will load, which
    would take the whole test session down with it rather than failing one
    test — and an installation can advertise a plugin directory holding an
    offscreen plugin it still can't load. So find out in a throwaway
    subprocess, where an abort costs nothing."""
    return subprocess.run(
        [sys.executable, "-c",
         "from PySide6.QtWidgets import QApplication; QApplication([])"],
        capture_output=True).returncode == 0


@pytest.fixture(scope="module")
def qapp():
    # conftest.py sets QT_QPA_PLATFORM=offscreen, so the real widget can be
    # built here rather than having the test re-implement its behaviour
    if QApplication.instance() is None and not _canCreateQApplication():
        pytest.skip("no usable Qt platform plugin for this interpreter")
    return QApplication.instance() or QApplication([])


def _generator(qapp):
    from xkoranate.tablegenerator.tablegenerator import XkorTableGenerator
    w = XkorTableGenerator()
    w.reset()
    return w


def test_ot_points_boxes_follow_the_win_loss_boxes_until_overridden(qapp):
    w = _generator(qapp)
    assert w.pointsForOTWin.value() == w.pointsForWin.value() == 3

    # a league switching to 2 points for a win gets 2-point OT wins too
    w.pointsForWin.setValue(2)
    assert w.pointsForOTWin.value() == 2
    assert w.pointsForSOWin.value() == 2

    w.pointsForLoss.setValue(0)
    w.pointsForOTLoss.setValue(1)  # the user overrides this one
    w.pointsForWin.setValue(3)
    assert w.pointsForOTWin.value() == 3  # still following
    assert w.pointsForOTLoss.value() == 1  # override survives


def test_only_overridden_ot_points_reach_the_table(qapp):
    w = _generator(qapp)
    w.pointsForWin.setValue(2)
    w.pointsForSOLoss.setValue(1)
    w.updateTable()

    assert w.t.getRawPointsForOTWin() is None  # never overridden
    assert w.t.getPointsForOTWin() == 2  # so it follows the win value
    assert w.t.getRawPointsForSOLoss() == 1


def test_opening_a_file_restores_which_ot_points_were_overridden(qapp, tmp_path):
    filename = os.path.join(str(tmp_path), "widget_round_trip.xml")

    w = _generator(qapp)
    w.pointsForWin.setValue(2)
    w.pointsForOTLoss.setValue(1)
    w.updateTable()
    XkorXmlTableWriter(filename, w.t)

    w2 = _generator(qapp)
    w2.openFile(filename)
    assert w2.pointsForOTLoss.value() == 1
    assert w2.pointsForOTLoss not in w2.linkedOTPoints  # still an override
    assert w2.pointsForOTWin in w2.linkedOTPoints  # still following
    w2.pointsForWin.setValue(4)
    assert w2.pointsForOTWin.value() == 4
    assert w2.pointsForOTLoss.value() == 1
