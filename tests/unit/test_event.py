import uuid

import pytest
from builders import make_athlete, make_event

from xkoranate.event import XkorEvent
from xkoranate.group import XkorGroup
from xkoranate.rplist import XkorRPList


def test_defaults():
    ev = XkorEvent()
    assert ev.name() == ""
    assert ev.sport() == ""
    assert ev.paradigm() == ""
    assert ev.competition() == ""
    assert ev.groups() == []
    assert ev.results() == {}


def test_setSport_sets_paradigm_too():
    ev = XkorEvent()
    ev.setSport("Athletics", "timed")
    assert ev.sport() == "Athletics"
    assert ev.paradigm() == "timed"


def test_setResult_clears_future_results_on_backtrack():
    ev = XkorEvent()
    ev.setResult(0, "md0")
    ev.setResult(1, "md1")
    ev.setResult(2, "md2")
    ev.setResult(1, "md1-redo")
    assert ev.results() == {0: "md0", 1: "md1-redo", 2: ""}


def test_addGroup_and_setGroups():
    ev = XkorEvent()
    g1 = XkorGroup("A")
    g2 = XkorGroup("B")
    ev.addGroup(g1)
    assert ev.groups() == [g1]
    ev.setGroups([g2])
    assert ev.groups() == [g2]


def test_replaceCompetitionOptions_merges_over_existing():
    ev = XkorEvent()
    ev.setCompetitionOptions({"a": 1, "b": 2})
    ev.replaceCompetitionOptions({"b": 20, "c": 3})
    assert ev.competitionOptions() == {"a": 1, "b": 20, "c": 3}


def test_makeStartList_without_rplist_uses_raw_skill():
    a1 = make_athlete("Alice", "AAA", 0.8)
    ev = make_event([a1])

    startList = ev.makeStartList(None)

    assert len(startList.groups) == 1
    assert startList.groups[0].name == "Group A"
    assert len(startList.groups[0].athletes) == 1
    assert startList.groups[0].athletes[0].rpSkill == pytest.approx(0.8)


def test_makeStartList_applies_rank_adjustment():
    a1 = make_athlete("Alice", "AAA", 1.0)
    a2 = make_athlete("Bob", "BBB", 3.0)
    ev = make_event([a1, a2])
    ev.signupList().setMinRank(1.0)
    ev.signupList().setMaxRank(3.0)

    startList = ev.makeStartList(None)

    skills = {a.name: a.rpSkill for a in startList.groups[0].athletes}
    assert skills["Alice"] == pytest.approx(0.0)
    assert skills["Bob"] == pytest.approx(1.0)


def test_makeStartList_olympic_style_blends_bonus_and_skill():
    a1 = make_athlete("Alice", "AAA", 0.5)
    ev = make_event([a1])

    rp = XkorRPList()
    rp.setRPCalculationType("olympic")
    rp.setRPEffect(20.0)
    rp.addBonus(("AAA", {"bonus": 1.0}))

    startList = ev.makeStartList(rp)

    athlete = startList.groups[0].athletes[0]
    expected = 1.0 * 0.2 + 0.5 * 0.8
    assert athlete.rpSkill == pytest.approx(expected)


def test_makeStartList_wg_style_scales_back_when_over_one():
    a1 = make_athlete("Alice", "AAA", 0.9)
    a2 = make_athlete("Bob", "BBB", 0.1)
    ev = make_event([a1, a2])

    rp = XkorRPList()
    rp.setRPCalculationType("relative")
    rp.setRPEffect(50.0)
    rp.addBonus(("AAA", {"bonus": 1.0}))
    rp.addBonus(("BBB", {"bonus": 0.0}))

    startList = ev.makeStartList(rp)

    skills = [a.rpSkill for a in startList.groups[0].athletes]
    assert max(skills) == pytest.approx(1.0)


def test_makeStartList_ignores_group_members_missing_from_signuplist():
    a1 = make_athlete("Alice", "AAA", 0.5, athlete_id=uuid.uuid4())
    ev = make_event([a1], groups=[[a1.id, uuid.uuid4()]])

    startList = ev.makeStartList(None)

    assert len(startList.groups[0].athletes) == 1
    assert startList.groups[0].athletes[0].name == "Alice"
