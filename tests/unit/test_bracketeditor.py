"""The event setup page in bracket mode: matches, byes and the draw buttons."""

import pytest

from xkoranate.athlete import BYE_ID, XkorAthlete
from xkoranate.competitions import bracket
from xkoranate.eventeditor.eventsetupdelegate import BYE_LABEL
from xkoranate.eventeditor.eventsetupwidget import XkorEventSetupWidget
from xkoranate.group import XkorGroup
from xkoranate.signuplist import XkorSignupList

CLUBS = [("Club %d" % (i + 1), "C%02d" % (i + 1), 100 - i * 5) for i in range(12)]


@pytest.fixture
def widget(qapp):
    sl = XkorSignupList()
    sl.setMinRank(0.0)
    sl.setMaxRank(100.0)
    for name, tla, rating in CLUBS:
        a = XkorAthlete()
        a.name, a.nation, a.skill = name, tla, float(rating)
        sl.addAthlete(a)

    w = XkorEventSetupWidget()
    w.setSignupList(sl)
    w.signupList = sl
    return w


def loadBracket(w, count=12):
    ids = [a.id for a in w.signupList.athletes()[:count]]
    w.setCompetition("singleElimination")
    w.setGroups([XkorGroup("Bracket", ids)])
    return ids


def pairs(w):
    rval = []
    for i in range(w.treeWidget.topLevelItemCount()):
        match = w.treeWidget.topLevelItem(i)
        rval.append(tuple(match.child(j).text(0) for j in range(match.childCount())))
    return rval


def realEntrants(w):
    return [i for i in w.bracketEntrants() if i not in (None, BYE_ID)]


def test_the_tree_holds_matches_not_groups(widget):
    loadBracket(widget)
    assert widget.treeWidget.topLevelItemCount() == 8  # 12 clubs -> 16-slot bracket
    assert all(len(p) == 2 for p in pairs(widget))
    assert [widget.treeWidget.topLevelItem(i).text(0) for i in range(8)] \
        == ["Match %d" % (i + 1) for i in range(8)]


def test_byes_are_shown_as_their_own_rows(widget):
    loadBracket(widget)
    flat = [name for p in pairs(widget) for name in p]
    assert flat.count("— BYE —") == 4
    assert widget.bracketEntrants().count(BYE_ID) == 4
    # and never two in the same match
    assert all(p.count("— BYE —") <= 1 for p in pairs(widget))


def test_groups_pools_the_matches_back_into_one_group(widget):
    ids = loadBracket(widget)
    groups = widget.groups()
    assert len(groups) == 1
    assert groups[0].name == "Bracket"
    assert len(groups[0].athletes) == 16
    assert sorted(realEntrants(widget), key=str) == sorted(ids, key=str)


def test_a_bracket_survives_a_round_trip_through_the_editor(widget):
    loadBracket(widget)
    widget.seedBracket()
    before = widget.groups()
    widget.setGroups(before)
    assert widget.groups()[0].athletes == before[0].athletes


def test_seeding_puts_the_byes_on_the_strongest_clubs(widget):
    loadBracket(widget)
    widget.seedBracket()
    byeHolders = set()
    for home, away in pairs(widget):
        if away == "— BYE —":
            byeHolders.add(home)
        elif home == "— BYE —":
            byeHolders.add(away)
    assert byeHolders == {"Club 1 (C01)", "Club 2 (C02)", "Club 3 (C03)", "Club 4 (C04)"}


def test_the_dice_redraws_the_whole_bracket(widget):
    loadBracket(widget)
    widget.seedBracket()
    seeded = list(widget.bracketEntrants())
    widget.randomizeGroup()
    drawn = list(widget.bracketEntrants())

    assert drawn != seeded
    assert sorted(realEntrants(widget), key=str) == sorted(
        [i for i in seeded if i not in (None, BYE_ID)], key=str)
    assert all(p.count("— BYE —") <= 1 for p in pairs(widget))


def test_spreading_seeds_keeps_them_in_separate_matches(widget):
    loadBracket(widget)
    widget.redrawBracket(lambda a, size: bracket.drawVariableSeeds(a, size, 4, widget.r))
    strongest = ["Club %d (C%02d)" % (i + 1, i + 1) for i in range(4)]
    matches = [i for i, p in enumerate(pairs(widget)) if any(n in strongest for n in p)]
    assert len(matches) == 4


def test_switching_to_a_league_drops_the_byes(widget):
    loadBracket(widget)
    widget.setCompetition("roundRobin")

    assert widget.headingLabel.text() == "Set up groups"
    groups = widget.groups()
    assert len(groups[0].athletes) == 12
    assert BYE_ID not in groups[0].athletes


def test_switching_to_a_bracket_repairs_the_entrants(widget):
    ids = [a.id for a in widget.signupList.athletes()]
    widget.setCompetition("roundRobin")
    widget.setGroups([XkorGroup("League", ids)])
    widget.setCompetition("singleElimination")

    assert widget.headingLabel.text() == "Set bracket"
    assert widget.treeWidget.topLevelItemCount() == 8
    assert sorted(realEntrants(widget), key=str) == sorted(ids, key=str)


def test_the_draw_buttons_are_only_offered_for_a_bracket(widget):
    widget.setCompetition("roundRobin")
    assert widget.insertGroupAction.isVisible()
    assert not widget.seedAction.isVisible()

    widget.setCompetition("singleElimination")
    assert not widget.insertGroupAction.isVisible()
    assert widget.seedAction.isVisible()
    assert widget.spreadSeedsAction.isVisible()


def test_a_hand_edited_bracket_is_repaired(widget):
    loadBracket(widget)
    # drop a club, leaving a match with a single entrant and an odd count
    ids = realEntrants(widget)[:11]
    widget.setBracketSlots(widget.padToBracket(ids))

    assert widget.treeWidget.topLevelItemCount() == 8
    assert all(p.count("— BYE —") <= 1 for p in pairs(widget))
    assert len(realEntrants(widget)) == 11
    assert widget.bracketEntrants().count(BYE_ID) == 5


def test_too_few_entrants_leaves_an_empty_bracket(widget):
    widget.setCompetition("singleElimination")
    widget.setGroups([XkorGroup("Bracket", [a.id for a in widget.signupList.athletes()[:1]])])
    assert widget.treeWidget.topLevelItemCount() == 0


def setSlot(w, match, child, label):
    """Set one slot through the delegate, as the combo editor does."""
    from PySide6.QtWidgets import QStyleOptionViewItem

    item = w.treeWidget.topLevelItem(match).child(child)
    index = w.treeWidget.indexFromItem(item, 0)
    editor = w._delegate.createEditor(w.treeWidget, QStyleOptionViewItem(), index)
    editor.setCurrentIndex(editor.findText(label))
    w._delegate.setModelData(editor, w.treeWidget.model(), index)


def test_bye_is_offered_as_a_slot_choice_in_a_bracket(widget):
    loadBracket(widget, 6)
    assert widget._delegate.allowBye
    assert widget._delegate.choices()[0] == BYE_LABEL


def test_bye_is_not_offered_outside_a_bracket(widget):
    widget.setCompetition("roundRobin")
    assert not widget._delegate.allowBye
    assert BYE_LABEL not in widget._delegate.choices()


def test_selecting_bye_puts_a_bye_in_that_slot(widget):
    loadBracket(widget, 6)
    before = widget.bracketEntrants().count(BYE_ID)

    # match 3 is a real fixture; give its away side a bye
    setSlot(widget, 2, 1, BYE_LABEL)

    assert widget.bracketEntrants().count(BYE_ID) == before + 1
    assert pairs(widget)[2][1] == BYE_LABEL


def test_a_match_of_two_byes_is_flagged(widget):
    loadBracket(widget, 6)
    setSlot(widget, 2, 1, BYE_LABEL)
    setSlot(widget, 2, 0, BYE_LABEL)

    label = widget.treeWidget.topLevelItem(2).text(0)
    assert "nobody in this match" in label
    # and the other match labels stay clean
    assert "nobody" not in widget.treeWidget.topLevelItem(0).text(0)
