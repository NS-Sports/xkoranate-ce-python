"""End-to-end integration test: app boot, event creation, scorination, save/load."""

import os
import sys
import uuid

import pytest

from xkoranate.application import XkorApplication
from xkoranate.athlete import BYE_ID, XkorAthlete
from xkoranate.competitions.competitionfactory import XkorCompetitionFactory
from xkoranate.event import XkorEvent
from xkoranate.group import XkorGroup
from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory
from xkoranate.rng import Mt19937
from xkoranate.rplist import XkorRPList
from xkoranate.signuplist import XkorSignupList
from xkoranate.xml.xmlindex import XkorXmlIndex
from xkoranate.xml.xmlreader import XkorXmlReader
from xkoranate.xml.xmlsportreader import XkorXmlSportReader
from xkoranate.xml.xmlwriter import XkorXmlWriter

NATIONS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]

SCORINATE_CASES = [
    ("Athletics—Men’s 00100 m—Round 1", None),
    ("Badminton—xkoranate formula", "matches"),
    ("Association football—SQIS formula", "roundRobin"),
    ("Association football—Footba11er formula", "matches"),
    ("Association football—LISA formula", "roundRobin"),
    ("Association football—LISA formula", "singleElimination"),
]


@pytest.fixture(scope="module")
def sport_index():
    # the "sports:" search path is registered by the application object, so
    # make sure one exists — otherwise this fixture only works when the
    # app-boot test happens to have run first
    app = XkorApplication.instance() or XkorApplication(sys.argv)
    app.refreshSearchPaths()
    index = XkorXmlIndex()
    index.traverse("sports:")
    return index


@pytest.fixture(scope="module")
def rng():
    return Mt19937(2026)


def build_event(index, rng, sportName, nAthletes=8):
    sportFile = index.lookup(sportName)
    reader = XkorXmlSportReader(sportFile)
    sport = reader.sport()
    sport.setPRNG(rng)

    sl = XkorSignupList()
    athletes = []
    for i in range(nAthletes):
        a = XkorAthlete()
        a.name = "Athlete %d" % (i + 1)
        a.nation = NATIONS[i % len(NATIONS)]
        a.skill = (i + 1) / float(nAthletes + 1)
        sl.addAthlete(a)
        athletes.append(a)

    ev = XkorEvent()
    ev.setName("Test " + sportName)
    ev.setSignupList(sl)
    ev.setSport(sportName, sport.paradigm())
    ev.addGroup(XkorGroup("Group A", [a.id for a in athletes]))
    return ev, sport


def scorinate(index, rng, sportName, competition=None):
    ev, sport = build_event(index, rng, sportName)
    par = XkorParadigmFactory.newParadigmForSport(sport, {})
    comp = competition or par.defaultCompetition()
    startList = ev.makeStartList(XkorRPList())
    c = XkorCompetitionFactory.newCompetitionFull(
        comp, startList, sport, ev.paradigmOptions(), ev.competitionOptions(), {})
    n = c.matchdays()
    outputs = []
    for md in range(n if n > 0 else 1):
        c.scorinate(md)
        outputs.append(c.results(md))
    return outputs


def test_app_boots_and_loads_sports():
    app = XkorApplication(sys.argv)
    app.loadSports()
    assert app.cw is not None


@pytest.mark.parametrize("sportName,competition", SCORINATE_CASES)
def test_scorinate_produces_results(sport_index, rng, sportName, competition):
    outputs = scorinate(sport_index, rng, sportName, competition)
    assert outputs
    assert outputs[0].strip() != ""


def test_save_load_roundtrip(sport_index, rng, tmp_path):
    ev, sport = build_event(sport_index, rng, "Athletics—Men’s 00100 m—Round 1")
    ev.setCompetition("standard")
    ev.setResult(0, "some result text\nline 2")
    rp = XkorRPList()
    rp.setCompetitionName("Test Cup")
    rp.addBonus(("AAA", {"bonus": 0.5}))

    xmlPath = str(tmp_path / "roundtrip.xml")
    XkorXmlWriter(xmlPath, rp, [(uuid.uuid4(), ev)])
    assert os.path.getsize(xmlPath) > 0

    r = XkorXmlReader(xmlPath)
    events2 = r.events()
    rp2 = r.rpList()
    ev2 = events2[0][1]

    assert ev2.name() == ev.name()
    assert ev2.sport() == ev.sport()
    assert ev2.competition() == "standard"
    assert len(ev2.signupList().athletes()) == len(ev.signupList().athletes())
    assert ev2.results()[0] == ev.results()[0]
    assert abs(rp2.bonus("AAA") - rp.bonus("AAA")) < 1e-12
    a1 = sorted(a.name for a in ev.signupList().athletes())
    a2 = sorted(a.name for a in ev2.signupList().athletes())
    assert a1 == a2
    g1 = ev.groups()[0]
    g2 = ev2.groups()[0]
    assert g1.name == g2.name and g1.athletes == g2.athletes


# ---------------------------------------------------------------- knockouts


def buildKnockout(index, rng, nAthletes, options=None, sportName="Association football—LISA formula",
                  draw=None):
    """An event set up as a single-elimination bracket, plus its start list.

    `draw` is the slot list the bracket editor would have produced; without
    one the entrants are left in signup order and the competition pads the
    bracket with byes itself.
    """
    ev, sport = build_event(index, rng, sportName, nAthletes=nAthletes)
    ev.setCompetition("singleElimination")
    ev.setCompetitionOptions(dict(options or {}))
    if draw is not None:
        ev.setGroups([XkorGroup("Bracket", draw)])
    return ev, sport, ev.makeStartList(XkorRPList())


def newKnockout(ev, sport, startList):
    return XkorCompetitionFactory.newCompetitionFull(
        "singleElimination", startList, sport, ev.paradigmOptions(),
        ev.competitionOptions(), ev.results())


def playKnockout(ev, sport, startList, upTo=None):
    """Play the bracket the way the GUI does: a fresh object per matchday."""
    c = newKnockout(ev, sport, startList)
    last = c.matchdays() if upTo is None else upTo
    for md in range(last):
        c.scorinate(md)
        ev.replaceCompetitionOptions(c.resumeFileOptions())
        ev.setResult(md, c.results(md))
        c = newKnockout(ev, sport, startList)
    return c


def test_single_elimination_round_names(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 12, None)
    c = newKnockout(ev, sport, sl)
    assert c.matchdays() == 4
    assert c.matchdayNames() == ["Round of 16", "Quarter-finals", "Semi-finals", "Final"]


def test_single_elimination_leaves_one_entrant_standing(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 12, None)
    c = playKnockout(ev, sport, sl)

    # the last round is a single match, so exactly one entrant comes out of it
    winners = c._winnersOfRound(c._rounds() - 1)
    assert winners is not None
    assert len(winners) == 1
    assert winners[0] is not None
    assert winners[0].name in ev.results()[c.matchdays() - 1]


def test_single_elimination_byes_appear_in_the_first_round_only(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 12, None)
    c = playKnockout(ev, sport, sl)

    assert "BYE" in ev.results()[0]
    assert ev.results()[0].count("BYE — advances") == 4  # 16-slot bracket, 12 entrants
    for md in range(1, c.matchdays()):
        assert "BYE" not in ev.results()[md]


@pytest.mark.parametrize("nAthletes", [2, 3, 5, 8, 11, 16])
def test_single_elimination_plays_out_for_any_size(sport_index, rng, nAthletes):
    ev, sport, sl = buildKnockout(sport_index, rng, nAthletes)
    c = playKnockout(ev, sport, sl)
    assert len(c._winnersOfRound(c._rounds() - 1)) == 1
    for md in range(c.matchdays()):
        assert ev.results()[md].strip() != ""


def test_single_elimination_third_place_playoff_is_its_own_matchday(sport_index, rng):
    ev, sport, sl = buildKnockout(
        sport_index, rng, 16, {"thirdPlacePlayoff": "true"})
    c = newKnockout(ev, sport, sl)
    assert c.matchdays() == 5  # four rounds plus the playoff
    assert c.matchdayNames() == [
        "Round of 16", "Quarter-finals", "Semi-finals", "Third-place playoff", "Final"]


def test_single_elimination_third_place_contests_the_beaten_semi_finalists(sport_index, rng):
    ev, sport, sl = buildKnockout(
        sport_index, rng, 16, {"thirdPlacePlayoff": "true"})
    c = playKnockout(ev, sport, sl)

    semiFinalRound = c._rounds() - 2
    losers = set(a.name for a in c._losersOfRound(semiFinalRound))
    assert len(losers) == 2

    playoff = ev.results()[3]
    for name in losers:
        assert name in playoff
    # and the winners of the semi-finals are contesting the final instead
    for winner in c._winnersOfRound(semiFinalRound):
        assert winner.name not in playoff


def test_single_elimination_revert_keeps_the_draw_and_earlier_rounds(sport_index, rng):
    ev, sport, sl = buildKnockout(
        sport_index, rng, 12, {"thirdPlacePlayoff": "true"})
    c = playKnockout(ev, sport, sl)

    draw = list(ev.competitionOptions()["bracketDraw"])
    rowsBefore = list(ev.competitionOptions()["bracketResults"])
    finalMatchday = c.matchdays() - 1

    ev.replaceCompetitionOptions(c.revertToMatchday(finalMatchday))
    c = newKnockout(ev, sport, sl)

    assert list(ev.competitionOptions()["bracketDraw"]) == draw
    rowsAfter = list(ev.competitionOptions()["bracketResults"])
    assert len(rowsAfter) == len(rowsBefore) - 1  # only the final is gone
    # the third-place playoff sits before the final, so it survives
    assert any(row.startswith("3P|") for row in rowsAfter)

    c.scorinate(finalMatchday)
    assert c.results(finalMatchday).strip() != ""
    assert len(c._winnersOfRound(c._rounds() - 1)) == 1


def test_single_elimination_revert_to_the_first_round_clears_the_draw(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 12, None)
    c = playKnockout(ev, sport, sl)

    options = c.revertToMatchday(0)
    assert options["bracketDraw"] == []
    assert options["bracketResults"] == []


def test_single_elimination_survives_a_save_load_roundtrip(sport_index, rng, tmp_path):
    ev, sport, sl = buildKnockout(
        sport_index, rng, 12, {"thirdPlacePlayoff": "true"})
    # play everything but the final, then reload and finish it
    finalMatchday = newKnockout(ev, sport, sl).matchdays() - 1
    playKnockout(ev, sport, sl, upTo=finalMatchday)

    xmlPath = str(tmp_path / "cup.xml")
    XkorXmlWriter(xmlPath, XkorRPList(), [(uuid.uuid4(), ev)])
    ev2 = XkorXmlReader(xmlPath).events()[0][1]

    assert ev2.competition() == "singleElimination"
    assert (list(ev2.competitionOptions()["bracketDraw"])
            == list(ev.competitionOptions()["bracketDraw"]))
    assert (list(ev2.competitionOptions()["bracketResults"])
            == list(ev.competitionOptions()["bracketResults"]))

    c2 = newKnockout(ev2, sport, ev2.makeStartList(XkorRPList()))
    assert c2.matchdays() - 1 == finalMatchday
    c2.scorinate(finalMatchday)
    assert c2.results(finalMatchday).strip() != ""
    assert len(c2._winnersOfRound(c2._rounds() - 1)) == 1


def test_single_elimination_schedule_shows_the_bracket_and_its_byes(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 12, None)
    c = newKnockout(ev, sport, sl)

    # the entrant order already describes a draw, so the pairings show up
    # before anything has been scorinated
    before = c.schedule()
    assert "12 entrants — 16-slot bracket, 4 byes" in before
    assert before.count("— BYE —") == 4

    playKnockout(ev, sport, sl, upTo=1)
    after = newKnockout(ev, sport, sl).schedule()
    assert "12 entrants — 16-slot bracket, 4 byes" in after
    assert after.count("— BYE —") == 4
    # once played, the stored draw is what's shown
    assert after.split("Round of 16")[1] == before.split("Round of 16")[1]


def test_single_elimination_plays_the_draw_the_bracket_editor_produced(sport_index, rng):
    """An explicit slot list — byes included — is played exactly as arranged."""
    ev, sport = build_event(sport_index, rng, "Association football—LISA formula", nAthletes=6)
    ids = [a.id for a in ev.signupList().athletes()]
    # 6 entrants in an 8-slot bracket: two byes, deliberately not at the top
    draw = [ids[0], ids[1], ids[2], BYE_ID, ids[3], ids[4], ids[5], BYE_ID]
    ev.setCompetition("singleElimination")
    ev.setGroups([XkorGroup("Bracket", draw)])
    sl = ev.makeStartList(XkorRPList())

    c = newKnockout(ev, sport, sl)
    fixtures = c._fixtures(0)
    names = [(h.name if h else None, a.name if a else None) for h, a in fixtures]
    byId = {a.id: a.name for a in ev.signupList().athletes()}
    assert names == [
        (byId[ids[0]], byId[ids[1]]),
        (byId[ids[2]], None),
        (byId[ids[3]], byId[ids[4]]),
        (byId[ids[5]], None),
    ]

    c.scorinate(0)
    result = c.results(0)
    assert result.count("BYE — advances") == 2
    assert byId[ids[2]] in result and byId[ids[5]] in result


def test_byes_are_stripped_for_competitions_that_do_not_understand_them(sport_index, rng):
    """The same group used for a league must not sprout phantom participants."""
    ev, sport = build_event(sport_index, rng, "Association football—LISA formula", nAthletes=6)
    ids = [a.id for a in ev.signupList().athletes()]
    ev.setGroups([XkorGroup("Bracket", ids[:3] + [BYE_ID] + ids[3:] + [BYE_ID])])
    sl = ev.makeStartList(XkorRPList())

    assert len(sl.groups[0].athletes) == 8  # byes survive into the start list

    knockout = XkorCompetitionFactory.newCompetitionFull(
        "singleElimination", sl, sport, ev.paradigmOptions(), {}, {})
    assert len(knockout.startList.groups[0].athletes) == 8
    assert len(knockout._realEntrants()) == 6

    for competition in ("roundRobin", "matches"):
        c = XkorCompetitionFactory.newCompetitionFull(
            competition, sl, sport, ev.paradigmOptions(), {}, {})
        assert len(c.startList.groups[0].athletes) == 6
        assert all(a.id != BYE_ID for a in c.startList.groups[0].athletes)


def test_schedule_names_the_matches_that_feed_later_rounds(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 8, {"thirdPlacePlayoff": "true"})
    schedule = newKnockout(ev, sport, sl).schedule()

    assert "Quarter-finals" in schedule
    # every match is numbered continuously, and later rounds refer back
    assert "5.  Match 1 winner" in schedule
    assert "6.  Match 3 winner" in schedule
    assert "8.  Match 5 winner" in schedule
    # the playoff is played before the final, so it takes the earlier number
    assert "7.  Match 5 loser" in schedule
    assert schedule.index("Third-place playoff") < schedule.index("Final")


def scheduleSection(schedule, heading):
    """The fixture lines under one round heading of a schedule."""
    lines = schedule.split("\n")
    start = lines.index(heading)  # the heading on a line of its own
    rval = []
    for line in lines[start + 1:]:
        if not line.strip():
            break
        rval.append(line)
    return rval


def test_schedule_fills_in_real_names_as_rounds_are_played(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 8, {"thirdPlacePlayoff": "true"})
    playKnockout(ev, sport, sl, upTo=1)  # quarter-finals only
    schedule = newKnockout(ev, sport, sl).schedule()

    # the semi-finals are known now, so they name entrants instead of matches
    semis = scheduleSection(schedule, "Semi-finals")
    assert len(semis) == 2
    for line in semis:
        assert "winner" not in line
        assert line.count("Athlete") == 2

    # the final still doesn't know who is in it
    final = scheduleSection(schedule, "Final")
    assert len(final) == 1
    assert "Match 5 winner" in final[0] and "Match 6 winner" in final[0]
