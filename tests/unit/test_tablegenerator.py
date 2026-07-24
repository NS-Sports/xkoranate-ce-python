import os
import re

from PySide6.QtCore import QRegularExpression

from xkoranate.tablegenerator.table import XkorTable
from xkoranate.tablegenerator.tablematch import XkorTableMatch
from xkoranate.tablegenerator.tablerow import XkorTableRow
from xkoranate.tablegenerator.tablesorter import XkorTableSorter
from xkoranate.xml.xmltablereader import XkorXmlTableReader
from xkoranate.xml.xmltablewriter import XkorXmlTableWriter

# the same pattern tablegenerator.py's generateMatches() and
# xmltablereader.py's readMatches() use to parse free-text match results
MATCH_RESULT_PATTERN = "([0-9]+)[-–:]([0-9]+)(?:\\s+(OT|SO))?"


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

    row = t.findTeam("Aquilla")
    assert row.wins() == 2
    assert t.getPoints(row) == 6
