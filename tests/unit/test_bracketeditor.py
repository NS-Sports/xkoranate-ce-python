"""The event setup page in bracket mode: matches, byes and the draw buttons."""

import uuid

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


def test_the_bracket_keeps_its_chosen_size_when_slots_are_emptied(widget):
    loadBracket(widget)
    # 12 clubs in a 16-slot bracket; take one out
    ids = realEntrants(widget)[:11]
    widget.setBracketSlots(widget.padToBracket(ids))

    assert widget.treeWidget.topLevelItemCount() == 8  # size is unchanged
    assert len(realEntrants(widget)) == 11
    assert widget.bracketEntrants().count(BYE_ID) == 5


def test_a_participant_can_never_be_placed_twice(widget):
    loadBracket(widget)
    ids = realEntrants(widget)
    # ask for a bracket with every club listed twice over
    widget.setBracketSlots(widget.padToBracket(ids + ids, size=32))

    placed = realEntrants(widget)
    assert len(placed) == len(set(placed)) == 12


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


def test_matches_cannot_be_deleted(widget):
    """Removing a match left a bracket that wasn't a power of two."""
    from PySide6.QtCore import QItemSelectionModel

    loadBracket(widget, 8)
    match = widget.treeWidget.topLevelItem(0)
    widget.treeWidget.setCurrentItem(match, 0, QItemSelectionModel.ClearAndSelect)
    assert not widget.deleteAction.isEnabled()

    widget.deleteAction.trigger()  # even if it somehow fires, nothing goes
    assert widget.treeWidget.topLevelItemCount() == 4


def test_clearing_a_slot_leaves_a_bye(widget):
    from PySide6.QtCore import QItemSelectionModel

    loadBracket(widget, 8)
    slot = widget.treeWidget.topLevelItem(0).child(0)
    widget.treeWidget.setCurrentItem(slot, 0, QItemSelectionModel.ClearAndSelect)
    assert widget.deleteAction.isEnabled()
    widget.deleteAction.trigger()

    assert widget.treeWidget.topLevelItemCount() == 4  # size unchanged
    assert len(realEntrants(widget)) == 7
    assert widget.bracketEntrants().count(BYE_ID) == 1


def test_add_all_fills_byes_without_duplicating(widget):
    """'Add all' used to append everyone again, so clubs played themselves."""
    from PySide6.QtCore import QItemSelectionModel

    loadBracket(widget, 12)  # every club in the signup list is placed
    assert widget.availableAthletes == []

    slot = widget.treeWidget.topLevelItem(0).child(0)
    widget.treeWidget.setCurrentItem(slot, 0, QItemSelectionModel.ClearAndSelect)
    widget.deleteAction.trigger()
    assert len(widget.availableAthletes) == 1  # the club we took out

    widget.insertAllAction.trigger()
    placed = realEntrants(widget)
    assert len(placed) == len(set(placed)) == 12
    assert widget.treeWidget.topLevelItemCount() == 8  # size unchanged
    assert widget.availableAthletes == []


def test_the_size_dropdown_resizes_the_bracket(widget):
    loadBracket(widget, 8)
    assert widget.bracketSize() == 8

    widget.setBracketSize(16)
    assert widget.treeWidget.topLevelItemCount() == 8
    assert len(realEntrants(widget)) == 8
    assert widget.bracketEntrants().count(BYE_ID) == 8
    assert widget.bracketSizeCombo.currentData() == 16


def test_shrinking_the_bracket_releases_the_clubs_that_no_longer_fit(widget):
    loadBracket(widget, 12)
    widget.setBracketSize(4)

    assert widget.treeWidget.topLevelItemCount() == 2
    assert len(realEntrants(widget)) == 4
    assert len(widget.availableAthletes) == 8  # the rest are back in the pool


def test_the_size_dropdown_is_only_shown_for_a_bracket(widget):
    widget.setCompetition("singleElimination")
    assert widget.bracketSizeCombo.isVisible() or not widget.isVisible()
    widget.setCompetition("roundRobin")
    assert not widget.bracketSizeCombo.isVisible()


def test_only_playable_bracket_sizes_are_offered(widget):
    """A 32-slot draw for four clubs leaves twelve matches empty, and the
    competition quietly plays a four-slot bracket instead."""
    loadBracket(widget, 4)
    sizes = [widget.bracketSizeCombo.itemData(i)
             for i in range(widget.bracketSizeCombo.count())]
    assert sizes == [2, 4, 8]  # at most one bye per match
    assert 32 not in sizes

    loadBracket(widget, 12)
    sizes = [widget.bracketSizeCombo.itemData(i)
             for i in range(widget.bracketSizeCombo.count())]
    assert sizes == [2, 4, 8, 16]  # smaller cups are allowed too


def test_a_smaller_bracket_can_be_chosen_than_the_field_needs(widget):
    """A 12-club signup list can still be run as a four-club cup."""
    loadBracket(widget, 12)
    widget.setBracketSize(4)

    assert widget.treeWidget.topLevelItemCount() == 2
    assert len(realEntrants(widget)) == 4
    assert widget.bracketEntrants().count(BYE_ID) == 0
    assert len(widget.availableAthletes) == 8


def test_the_offered_sizes_follow_the_entrant_count(widget):
    from PySide6.QtCore import QItemSelectionModel

    loadBracket(widget, 8)
    assert 16 in [widget.bracketSizeCombo.itemData(i)
                  for i in range(widget.bracketSizeCombo.count())]

    # empty four slots; 16 is no longer playable with four entrants
    for match in range(4):
        slot = widget.treeWidget.topLevelItem(match).child(1)
        widget.treeWidget.setCurrentItem(slot, 0, QItemSelectionModel.ClearAndSelect)
        widget.deleteAction.trigger()
    assert len(realEntrants(widget)) == 4
    assert 16 not in [widget.bracketSizeCombo.itemData(i)
                      for i in range(widget.bracketSizeCombo.count())]


def test_add_all_grows_the_bracket_to_hold_everyone(widget):
    """After shrinking, "add all" filled only the gaps — so the participants
    that no longer fitted could not get back in without enlarging the bracket
    one step at a time."""
    loadBracket(widget, 12)
    widget.setBracketSize(2)
    assert len(realEntrants(widget)) == 2
    assert len(widget.availableAthletes) == 10

    widget.insertAllAction.trigger()

    assert len(realEntrants(widget)) == 12
    assert widget.availableAthletes == []
    assert widget.bracketSize() == 16
    # and the byes are still spread one to a match
    assert all(p.count("— BYE —") <= 1 for p in pairs(widget))


def openEditor(w, item):
    """Open a slot's editor the way the view does, and return (editor, index)."""
    from PySide6.QtWidgets import QStyleOptionViewItem

    index = w.treeWidget.indexFromItem(item, 0)
    editor = w._delegate.createEditor(w.treeWidget, QStyleOptionViewItem(), index)
    w._delegate.setEditorData(editor, index)
    return editor, index


def test_opening_an_occupied_slot_offers_whoever_is_in_it(widget):
    """Only unplaced participants are on offer, so without this the occupant
    of a slot isn't in its own dropdown."""
    loadBracket(widget, 12)
    assert widget.availableAthletes == []  # everyone is placed

    slot = widget.treeWidget.topLevelItem(4).child(0)
    editor, _ = openEditor(widget, slot)

    assert slot.text(0) in [editor.itemText(i) for i in range(editor.count())]
    assert editor.currentText() == slot.text(0)


def test_closing_a_slot_editor_without_choosing_leaves_it_alone(widget):
    """Merely opening the dropdown used to blank the slot to
    "<unknown participant>" on the way out."""
    loadBracket(widget, 12)
    slot = widget.treeWidget.topLevelItem(4).child(0)
    before = slot.text(0)

    editor, index = openEditor(widget, slot)
    widget._delegate.setModelData(editor, widget.treeWidget.model(), index)

    assert slot.text(0) == before
    assert "unknown" not in slot.text(0)


def test_a_cleared_participant_can_be_put_back(widget):
    from PySide6.QtCore import QItemSelectionModel

    loadBracket(widget, 12)
    slot = widget.treeWidget.topLevelItem(0).child(0)
    name = slot.text(0)

    widget.treeWidget.setCurrentItem(slot, 0, QItemSelectionModel.ClearAndSelect)
    widget.deleteAction.trigger()
    assert slot.text(0) == "— BYE —"

    editor, index = openEditor(widget, slot)
    editor.setCurrentIndex(editor.findText(name))
    widget._delegate.setModelData(editor, widget.treeWidget.model(), index)

    assert slot.text(0) == name
    placed = realEntrants(widget)
    assert len(placed) == len(set(placed)) == 12


def test_a_slot_can_still_be_swapped_for_a_free_participant(widget):
    from PySide6.QtCore import QItemSelectionModel

    loadBracket(widget, 12)
    # free one club up by clearing its slot
    cleared = widget.treeWidget.topLevelItem(0).child(0)
    freed = cleared.text(0)
    widget.treeWidget.setCurrentItem(cleared, 0, QItemSelectionModel.ClearAndSelect)
    widget.deleteAction.trigger()

    other = widget.treeWidget.topLevelItem(5).child(1)
    editor, index = openEditor(widget, other)
    editor.setCurrentIndex(editor.findText(freed))
    widget._delegate.setModelData(editor, widget.treeWidget.model(), index)

    assert other.text(0) == freed
    placed = realEntrants(widget)
    assert len(placed) == len(set(placed))  # nobody placed twice


def clearSlots(w, count):
    """Clear `count` occupied slots the way selecting rows and hitting Delete does."""
    cleared = 0
    for i in range(w.treeWidget.topLevelItemCount()):
        match = w.treeWidget.topLevelItem(i)
        for j in range(match.childCount()):
            if cleared >= count:
                return
            if match.child(j).text(0) != BYE_LABEL:
                w.treeWidget.clearSelection()
                match.child(j).setSelected(True)
                w.deleteItems()
                cleared += 1


def test_the_draw_buttons_survive_a_bracket_emptied_down_to_a_few(widget):
    """bracketSlotCount outlives the entrants that justified it.

    Clearing slots leaves byes behind without shrinking the bracket, so a
    16-slot draw could be asked to hold 12 byes — which byeSlots() refuses,
    one bye per match being its whole contract. The buttons stayed enabled
    and the ValueError came straight out of the toolbar handler.
    """
    loadBracket(widget, 12)
    assert widget.bracketSlotCount == 16
    clearSlots(widget, 8)
    assert len(realEntrants(widget)) == 4

    for draw in (widget.seedBracket, widget.randomizeGroup):
        draw()  # must not raise
        assert len(realEntrants(widget)) == 4
        # clamped to a bracket the draw can actually fill
        assert widget.bracketSlotCount == 8
        assert all(p.count(BYE_LABEL) <= 1 for p in pairs(widget))


def test_largest_drawable_size_never_leaves_an_empty_match(widget):
    for entrants in range(2, 40):
        size = widget.largestDrawableSize(entrants)
        assert size & (size - 1) == 0  # a power of two
        assert size >= bracket.bracketSize(entrants)
        assert size - entrants <= size // 2  # at most one bye per match
        bracket.byeSlots(size, size - entrants)  # must not raise


def test_growing_the_bracket_spreads_the_byes_one_to_a_match(widget):
    """Padding at the tail left the last matches holding nobody.

    drawFromOrder() rejects a bracket with an empty match and silently
    re-pairs it, so the tournament shown on the page was not the one played.
    """
    ids = loadBracket(widget, 6)
    widget.setBracketSize(4)  # drops two clubs
    assert len(realEntrants(widget)) == 4
    widget.setBracketSize(8)  # and grow again

    assert widget.treeWidget.topLevelItemCount() == 4
    assert all(p.count(BYE_LABEL) == 1 for p in pairs(widget)), pairs(widget)
    assert len(realEntrants(widget)) == 4


def test_a_grown_bracket_is_played_as_shown(widget):
    """The slot list the editor leaves behind must survive drawFromOrder()."""
    loadBracket(widget, 6)
    widget.setBracketSize(4)
    widget.setBracketSize(8)

    entrants = widget.bracketEntrants()
    real = [i for i in entrants if i != BYE_ID]
    slots = [None if i == BYE_ID else i for i in entrants]
    assert bracket.isWellFormed(slots, real)


def test_the_bracket_size_never_exceeds_what_can_be_filled(widget):
    loadBracket(widget, 12)
    widget.setBracketSize(2)  # down to two clubs
    widget.setBracketSize(128)  # a size nothing could fill

    assert widget.bracketSlotCount == 4
    assert all(p.count(BYE_LABEL) <= 1 for p in pairs(widget))


def test_switching_to_a_bracket_and_back_keeps_the_pools(widget):
    """A bracket is one pooled group; the pools must survive the round trip.

    Clicking the format dropdown to see what a cup would look like used to
    merge every pool into one and keep only the first pool's name, with no
    confirmation and no way back.
    """
    ids = [a.id for a in widget.signupList.athletes()[:8]]
    widget.setCompetition("roundRobin")
    widget.setGroups([XkorGroup("Pool A", ids[:4]), XkorGroup("Pool B", ids[4:])])
    before = [(g.name, list(g.athletes)) for g in widget.groups()]
    assert len(before) == 2

    widget.setCompetition("singleElimination")
    assert len(widget.groups()) == 1  # pooled, as a bracket must be

    widget.setCompetition("roundRobin")
    assert [(g.name, list(g.athletes)) for g in widget.groups()] == before


def test_the_pools_are_not_restored_over_a_changed_field(widget):
    """Once the bracket's entrants change, the old pools no longer describe it."""
    ids = [a.id for a in widget.signupList.athletes()[:8]]
    widget.setCompetition("roundRobin")
    widget.setGroups([XkorGroup("Pool A", ids[:4]), XkorGroup("Pool B", ids[4:])])

    widget.setCompetition("singleElimination")
    widget.setBracketSize(4)  # drops half the field
    widget.setCompetition("roundRobin")

    groups = widget.groups()
    assert len(groups) == 1
    assert len([i for i in groups[0].athletes if i != BYE_ID]) == 4


def test_the_edit_paths_ask_before_discarding_results(widget):
    """Rearranging a bracket drops the results played from it — silently.

    The competition is right to drop them, but the user was only told later,
    by finding the results pane blank.
    """
    loadBracket(widget, 8)
    before = list(widget.bracketEntrants())
    asked = []
    widget.resultsGuard = lambda: (asked.append(1), False)[1]  # "Cancel"

    widget.setBracketSize(4)
    assert widget.bracketEntrants() == before
    assert len(asked) == 1

    widget._resultsGuardAsked = False
    widget.seedBracket()
    assert widget.bracketEntrants() == before
    assert len(asked) == 2

    widget._resultsGuardAsked = False
    match = widget.treeWidget.topLevelItem(0)
    widget.treeWidget.clearSelection()
    match.child(0).setSelected(True)
    widget.deleteItems()
    assert widget.bracketEntrants() == before
    assert len(asked) == 3


def test_the_bracket_is_only_guarded_once_per_event(widget):
    """Having said "discard", the user isn't asked again for every nudge."""
    loadBracket(widget, 8)
    asked = []
    widget.resultsGuard = lambda: (asked.append(1), True)[1]  # "Discard"

    widget.setBracketSize(4)
    widget.seedBracket()
    widget.randomizeGroup()
    assert len(asked) == 1

    # a freshly loaded event has its own results to protect
    loadBracket(widget, 8)
    widget.setBracketSize(4)
    assert len(asked) == 2


def test_a_declined_drag_puts_the_bracket_back(widget):
    """A drop can't be vetoed, so reflow undoes it instead."""
    loadBracket(widget, 8)
    before = list(widget.bracketEntrants())
    widget.resultsGuard = lambda: False

    # move a row between matches, as an internal drag does
    first = widget.treeWidget.topLevelItem(0)
    second = widget.treeWidget.topLevelItem(1)
    second.addChild(first.takeChild(0))
    widget.reflowBracket()

    assert widget.bracketEntrants() == before


def test_group_setup_still_offers_a_participant_already_in_a_group(widget):
    """Filtering placed participants is a bracket rule, not a global one.

    A participant has always been allowed in more than one group, and the
    file format represents it; making the filter unconditional quietly
    changed how every other competition type is set up.
    """
    ids = [a.id for a in widget.signupList.athletes()[:4]]
    widget.setCompetition("roundRobin")
    widget.setGroups([XkorGroup("Pool A", ids), XkorGroup("Pool B", [])])

    assert set(ids) <= set(widget.availableAthletes)


def test_a_bracket_does_not_offer_a_participant_already_in_the_draw(widget):
    ids = loadBracket(widget, 8)
    assert not (set(ids) & set(widget.availableAthletes))


def test_a_drag_that_unbalances_a_match_is_repaired(widget):
    """The whole point of the deferred reflow: a drop can leave a match
    holding one or three entrants, and drawFromOrder() would then reject the
    bracket and silently re-pair it."""
    loadBracket(widget, 8)
    first = widget.treeWidget.topLevelItem(0)
    second = widget.treeWidget.topLevelItem(1)
    second.addChild(first.takeChild(0))  # 1 here, 3 there
    assert [len(p) for p in pairs(widget)][:2] == [1, 3]

    widget.reflowBracket()

    assert all(len(p) == 2 for p in pairs(widget))
    assert len(realEntrants(widget)) == 8


def test_deleting_a_participant_leaves_a_bracket_that_is_still_a_power_of_two(widget):
    """deleteAthlete() takes the row out entirely, which would leave 15 slots."""
    ids = loadBracket(widget, 8)
    widget.deleteAthlete(ids[0])
    widget.reflowBracket()

    slots = widget.bracketEntrants()
    assert len(slots) & (len(slots) - 1) == 0
    assert all(len(p) == 2 for p in pairs(widget))
    assert ids[0] not in slots


def test_the_spread_seeds_button_asks_how_many_and_uses_the_answer(widget, monkeypatch):
    """The handler itself, not just the draw underneath it: the dialog bounds
    and the cancel path had no coverage."""
    from PySide6.QtWidgets import QInputDialog

    loadBracket(widget, 8)
    asked = {}

    def getInt(parent, title, label, value, minValue, maxValue):
        asked.update(value=value, minValue=minValue, maxValue=maxValue)
        return 4, True

    monkeypatch.setattr(QInputDialog, "getInt", staticmethod(getInt))
    widget.spreadSeeds()

    assert asked == {"value": 4, "minValue": 2, "maxValue": 8}
    assert len(realEntrants(widget)) == 8


def test_cancelling_the_seed_count_leaves_the_bracket_alone(widget, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    loadBracket(widget, 8)
    before = list(widget.bracketEntrants())
    monkeypatch.setattr(QInputDialog, "getInt",
                        staticmethod(lambda *a, **k: (4, False)))
    widget.spreadSeeds()

    assert widget.bracketEntrants() == before


def test_choosing_a_size_in_the_dropdown_resizes_the_bracket(widget):
    """setBracketSize() is well covered; the combo wiring into it was not."""
    loadBracket(widget, 8)
    index = widget.bracketSizeCombo.findData(4)
    assert index >= 0
    widget.bracketSizeCombo.setCurrentIndex(index)

    assert widget.bracketSlotCount == 4
    assert len(realEntrants(widget)) == 4
    # and the combo still shows what the bracket actually is
    assert widget.bracketSizeCombo.currentData() == 4


def test_selection_changes_do_not_rebuild_the_available_list(widget):
    """updateButtons() runs on every selection change and used to walk the
    whole signup list each time, on the UI thread."""
    loadBracket(widget, 8)
    calls = []
    realAthletes = widget.sl.athletes

    def counted():
        calls.append(1)
        return realAthletes()

    widget.sl.athletes = counted
    for i in range(widget.treeWidget.topLevelItemCount()):
        widget.treeWidget.clearSelection()
        widget.treeWidget.topLevelItem(i).setSelected(True)
        widget.updateButtons()

    assert calls == []


def test_the_available_list_still_follows_the_placements(widget):
    ids = loadBracket(widget, 6)  # 6 clubs in an 8-slot bracket
    assert ids[0] not in widget.availableAthletes

    widget.treeWidget.clearSelection()
    for i in range(widget.treeWidget.topLevelItemCount()):
        match = widget.treeWidget.topLevelItem(i)
        for j in range(match.childCount()):
            if match.child(j).text(0) != BYE_LABEL:
                match.child(j).setSelected(True)
                widget.deleteItems()
                widget.updateButtons()
                assert ids[0] in widget.availableAthletes
                return
    raise AssertionError("no occupied slot found")


def test_a_new_signup_list_refreshes_the_available_list(widget):
    loadBracket(widget, 4)
    widget.updateButtons()

    sl = XkorSignupList()
    sl.setMinRank(0.0)
    sl.setMaxRank(100.0)
    a = XkorAthlete()
    a.name, a.nation, a.skill = "Late Entry", "LTE", 50.0
    # XkorSignupList.generateID() draws from the list's own seeded RNG, so a
    # fresh list hands out the same ids as the one the bracket was built from
    a.id = uuid.uuid4()
    sl.addAthlete(a)
    widget.setSignupList(sl)
    widget.signupList = sl
    widget.updateButtons()

    assert "Late Entry (LTE)" in widget.availableAthleteNames


@pytest.mark.parametrize("asked,expected", [(0, 2), (1, 2), (3, 4), (5, 8), (9, 16), (999, 16)])
def test_setBracketSize_snaps_to_a_power_of_two(widget, asked, expected):
    """A size that isn't one makes drawFromOrder() reject the slot list and
    silently re-pair it. The combo can't produce one, but this is the public
    method and the one the tests themselves use."""
    loadBracket(widget, 12)
    widget.setBracketSize(asked)

    size = widget.bracketSlotCount
    assert size == expected
    assert size & (size - 1) == 0
    assert all(len(p) == 2 for p in pairs(widget))
