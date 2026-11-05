import os
import re

from builders import make_table, names, points
from PySide6.QtCore import QRegularExpression

from xkoranate.tablegenerator.decider import (MATCH_RESULT_PATTERN, classify,
                                              parseMatchLine,
                                              stripTrailingDeciders)
from xkoranate.tablegenerator.tablematch import XkorTableMatch
from xkoranate.tablegenerator.tablerow import XkorTableRow
from xkoranate.tablegenerator.tablesorter import XkorTableSorter
from xkoranate.xml.xmltablereader import XkorXmlTableReader
from xkoranate.xml.xmltablewriter import XkorXmlTableWriter


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
    t = make_table()
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
    t = make_table(2, 2, 0, ot_win=2, so_win=2, ot_loss=1, so_loss=1)
    # 3 wins (all worth 2) + 1 OT loss (1) + 1 SO loss (1) + 1 regulation loss (0)
    assert t.getPoints(row) == 3 * 2 + 1 + 1 + 0


def test_ot_so_points_fall_back_to_win_loss_when_unset():
    row = _row_with_matches((1, 3, True, "OT"), (3, 1, True, "SO"))
    t = make_table()
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


def test_win_percentage_ignoring_draws_survives_a_side_that_has_only_drawn():
    t = make_table(criteria=["winPercentNFL"],
                   matches=[("Alpha", "Bravo", 1, 1), ("Charlie", "Delta", 2, 0)])

    t.generate()  # was a ZeroDivisionError for Alpha and Bravo

    assert names(t)[0] == "Charlie"
    assert set(names(t)[1:]) == {"Alpha", "Bravo", "Delta"}


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

    t = make_table(2, 2, 0, matches=[("Aquilla", "Busby", 3, 2, "OT"), ("Busby", "Aquilla", 1, 4, "SO")],
                   ot_win=2, so_win=2, ot_loss=1, so_loss=1)
    t.setShowOvertime(True)

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

    t = make_table()
    XkorXmlTableWriter(filename, t)
    with open(filename, encoding="utf-8") as f:
        assert "pointsForOTWin" not in f.read()

    reloaded = XkorXmlTableReader(filename).table()
    assert reloaded.getRawPointsForOTWin() is None
    reloaded.setPointsForWin(2)
    assert reloaded.getPointsForOTWin() == 2


def test_saving_a_table_that_does_override_ot_points_keeps_the_override(tmp_path):
    filename = os.path.join(str(tmp_path), "overrides.xml")

    t = make_table(win=2, ot_loss=1)
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
    assert parseMatchLine("Aquilla 3–2 OTtawa") == ("Aquilla", "OTtawa", 3.0, 2.0, None)
    assert parseMatchLine("Aquilla 3–2 SOuthampton") == (
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
    assert parseMatchLine("Aquilla 2–2 Busby (3–2 OT)") == ("Aquilla", "Busby", 3.0, 2.0, "OT")
    assert parseMatchLine("Aquilla 2–2 Busby (1–0 SO)") == ("Aquilla", "Busby", 3.0, 2.0, "SO")
    assert parseMatchLine("Charlie 2–2 Dorset (2–2 AET) (3–4 pen.)") == (
        "Charlie", "Dorset", 2.0, 3.0, "SO")


def test_manual_entry_still_recognizes_the_original_inline_marker():
    assert parseMatchLine("Aquilla 3–2 OT Busby") == ("Aquilla", "Busby", 3.0, 2.0, "OT")
    assert parseMatchLine("Aquilla 1–4 SO Busby") == ("Aquilla", "Busby", 1.0, 4.0, "SO")


def test_manual_entry_unaffected_when_theres_no_decider_at_all():
    assert parseMatchLine("Aquilla 3–1 Busby") == ("Aquilla", "Busby", 3.0, 1.0, None)


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


def test_coin_flip_values_survive_qNumber_exactly():
    # qNumber() writes 6 significant digits, so a flip that isn't a whole
    # number under a million would reload as a different value
    from xkoranate.variant import qNumber, toDouble

    rows = [XkorTableRow("Team %d" % i) for i in range(50)]
    sorter = XkorTableSorter()
    sorter.sort(rows, "coinFlip")

    flips = sorter.getCoinFlips()
    assert len(set(flips.values())) == len(flips)  # no two teams tied
    for value in flips.values():
        assert toDouble(qNumber(value)) == value


def test_coin_flips_are_dropped_for_teams_the_table_no_longer_has():
    t = make_table(criteria=["coinFlip"], matches=[("Aquilla", "Busby", 1, 1)])
    t.generate()
    assert set(t.getCoinFlips()) == {"Aquilla", "Busby"}

    # the user fixes a typo in a team name and regenerates
    t.setMatches([XkorTableMatch("Aquila", "Busby", 1, 1)])
    t.generate()
    assert set(t.getCoinFlips()) == {"Aquila", "Busby"}


def test_coin_flip_result_survives_an_xml_save_and_reload(tmp_path):
    filename = os.path.join(str(tmp_path), "coin_flip_table.xml")

    t = make_table(criteria=["points", "coinFlip"],
                   matches=[("Aquilla", "Busby", 1, 1), ("Busby", "Aquilla", 1, 1)])
    t.generate()
    originalOrder = [row[0].name() for row in t.data]
    assert sorted(originalOrder) == ["Aquilla", "Busby"]  # tied on everything but the coin flip

    XkorXmlTableWriter(filename, t)

    reader = XkorXmlTableReader(filename)
    assert not reader.hasError()
    reloaded = reader.table()
    reloaded.generate()

    assert [row[0].name() for row in reloaded.data] == originalOrder


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


def test_the_match_results_box_parses_through_the_shared_parser(qapp):
    w = _generator(qapp)
    w.matches.setPlainText("Aquilla 2–2 Busby (3–2 OT)\n"
                           "Busby 3–2 SO Charlie\n"
                           "Charlie 1–0 OTtawa\n")
    w.generateMatches()

    assert [(m.team1, m.team2, m.score1, m.score2, m.decider)
            for m in w.matchesList] == [
        ("Aquilla", "Busby", 3.0, 2.0, "OT"),
        ("Busby", "Charlie", 3.0, 2.0, "SO"),
        ("Charlie", "OTtawa", 1.0, 0.0, None),
    ]
    assert "OTtawa" in w.teamsList


def _conferenceTable(teams=None):
    """A and B share a conference; X is from another one. A and B are level
    on points, but A won the head-to-head."""
    t = make_table(criteria=["points", "h2hPoints", "goalDifference"],
                   matches=[("A", "X", 0, 3), ("B", "X", 3, 0), ("A", "B", 1, 0), ("B", "X", 0, 5)])
    t.setTeams(teams)
    t.generate()
    return names(t)


def test_a_team_filter_keeps_only_those_teams_in_the_table():
    assert _conferenceTable(["A", "B"]) == ["A", "B"]


def test_a_team_filter_still_counts_games_against_teams_outside_it():
    t = make_table(matches=[("A", "X", 2, 0), ("A", "B", 1, 1)])
    t.setTeams(["A", "B"])
    t.generate()
    rows = {row.name(): row for tier in t.data for row in tier}
    assert set(rows) == {"A", "B"}
    assert rows["A"].played() == 2
    assert rows["B"].played() == 1


def test_head_to_head_breaks_a_tie_inside_a_filtered_table():
    # level on points and goal difference; A won the meeting
    t = make_table(criteria=["points", "h2hPoints"],
                   matches=[("A", "X", 0, 1), ("B", "X", 1, 0), ("B", "A", 0, 1)])
    t.setTeams(["B", "A"])
    t.generate()
    assert names(t) == ["A", "B"]


def test_an_unfiltered_table_shows_every_team():
    assert sorted(_conferenceTable()) == ["A", "B", "X"]
    assert sorted(_conferenceTable(None)) == ["A", "B", "X"]


def _crossTable(crossPoints, conferences=None):
    """A (East) beats B (East) and loses to X (West); B beats X; C (East)
    draws with X."""
    t = make_table(criteria=["points"],
                   matches=[("A", "B", 2, 0), ("A", "X", 0, 1), ("B", "X", 1, 0), ("C", "X", 1, 1)])
    t.setConferences(conferences or {"A": 0, "B": 0, "C": 0, "X": 1})
    t.setCrossPoints(crossPoints)
    t.generate()
    return t, points(t)


def test_cross_conference_games_score_their_own_points():
    t, scored = _crossTable((2, 0, 1))
    # A: in-conference win 3, cross loss 1
    assert scored == {"A": 4, "B": 2, "C": 0, "X": 2 + 1 + 0}


def test_without_cross_points_every_game_scores_alike():
    t, scored = _crossTable(None)
    assert scored == {"A": 3, "B": 3, "C": 1, "X": 3 + 0 + 1}


def test_the_points_sort_uses_cross_points():
    # with cross wins worth 5, B (cross win) passes A (conference win)
    t, scored = _crossTable((5, 1, 0))
    order = names(t)
    assert order.index("B") < order.index("A")


def test_teams_without_a_conference_never_count_as_cross():
    t, scored = _crossTable((2, 0, 1), conferences={"A": 0})
    assert scored == {"A": 3, "B": 3, "C": 1, "X": 3 + 0 + 1}


def test_an_overtime_cross_game_keeps_its_overtime_points():
    t = make_table(matches=[("A", "X", 2, 1, "OT")], ot_win=2, ot_loss=1)
    t.setConferences({"A": 0, "X": 1})
    t.setCrossPoints((1, 0, 0))
    t.generate()
    assert points(t) == {"A": 2, "X": 1}


def test_a_shootout_cross_game_follows_cross_points_when_so_points_are_unset():
    t = make_table(criteria=["points"], matches=[("A", "X", 1.01, 1, "SO")])
    t.setConferences({"A": 0, "X": 1})
    t.setCrossPoints((1, 0, 0))
    t.generate()
    assert points(t) == {"A": 1, "X": 0}
