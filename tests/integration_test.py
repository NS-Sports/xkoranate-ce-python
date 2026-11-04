"""End-to-end integration test: app boot, event creation, scorination, save/load."""

import os
import sys
import uuid

import pytest

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QApplication

from xkoranate.application import XkorApplication
from xkoranate.athlete import BYE_ID, XkorAthlete
from xkoranate.competitions.competitionfactory import XkorCompetitionFactory
from xkoranate.event import XkorEvent
from xkoranate.eventeditor.eventeditor import XkorEventEditor
from xkoranate.group import XkorGroup
from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory
from xkoranate.paths import sportsDir
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


@pytest.fixture
def rng():
    """A fresh seeded generator per test.

    Module scope shared one stream across the whole file, so how far into it
    any given test started depended on which tests ran before it. Running a
    subset, or inserting a test above an existing one, silently changed every
    later test's numbers — fine for today's structural assertions, a
    heisenbug for the first outcome-sensitive one.
    """
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


# ------------------------------------------------- editor round trips


@pytest.fixture(scope="module")
def editor(sport_index):
    """The real event editor, with the sport list loaded."""
    app = XkorApplication.instance() or XkorApplication(sys.argv)
    app.loadSports()
    return app.cw


def selectedCompetition(cw):
    from PySide6.QtCore import Qt

    box = cw.ee.competitionSelector.comboBox
    return box.itemData(box.currentIndex(), Qt.UserRole)


@pytest.mark.parametrize("competition", ["singleElimination", "matches", "roundRobin"])
def test_opening_an_event_keeps_its_competition_type(editor, sport_index, rng, competition):
    """Rebuilding the selectors used to report a type back over the loaded one.

    The combo box fires currentIndexChanged as it is repopulated, and each of
    those wrote a competition type into the event being loaded — so anything
    that wasn't the first item in the list was silently replaced.
    """
    ev, sport = build_event(sport_index, rng, "Association football—LISA formula")
    ev.setCompetition(competition)

    editor.showEventEditor(ev)
    assert selectedCompetition(editor) == competition
    assert editor.ee.m_data.competition() == competition

    # page to the end of the wizard and back
    for _ in range(4):
        editor.ee.goNext()
    for _ in range(4):
        editor.ee.goPrev()
    assert selectedCompetition(editor) == competition

    # and leaving the event must not rewrite it
    editor.updateCurrentEvent()
    assert ev.competition() == competition


# ------------------------------------------------- round output and staleness


def test_a_round_names_the_next_round_s_pairings(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    playKnockout(ev, sport, sl, upTo=1)  # quarter-finals

    result = ev.results()[0]
    assert "Into the Semi-finals" in result
    assert "Advancing" not in result
    # two semi-finals, each naming both winners
    section = result.split("Into the Semi-finals")[1].strip().split("\n")
    assert len([line for line in section if line.strip()]) == 2
    for line in section:
        if line.strip():
            assert line.count("Athlete") == 2


def test_the_last_round_names_the_champion(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    c = playKnockout(ev, sport, sl)

    final = ev.results()[c.matchdays() - 1]
    assert "Champion" in final
    assert "Into the" not in final


def test_a_bracket_larger_than_the_field_keeps_the_size_it_was_given(sport_index, rng):
    """The slot list is the bracket size, not bracketSize(entrant count).

    Four entrants deliberately drawn as eight quarter-finals used to be
    re-sized to a four-slot bracket and re-paired, so the semi-finals played
    were pairings that appeared nowhere on the setup page.
    """
    ev, sport = build_event(sport_index, rng, "Association football—LISA formula", nAthletes=4)
    ids = [a.id for a in ev.signupList().athletes()]
    draw = [ids[0], BYE_ID, ids[1], BYE_ID, ids[2], BYE_ID, ids[3], BYE_ID]
    ev.setCompetition("singleElimination")
    ev.setGroups([XkorGroup("Bracket", draw)])
    sl = ev.makeStartList(XkorRPList())

    c = newKnockout(ev, sport, sl)
    assert c.matchdays() == 3  # quarter-finals, semi-finals, final

    byId = {a.id: a.name for a in ev.signupList().athletes()}
    fixtures = c._fixtures(0)
    assert [(h.name if h else None, a.name if a else None) for h, a in fixtures] == [
        (byId[ids[0]], None),
        (byId[ids[1]], None),
        (byId[ids[2]], None),
        (byId[ids[3]], None),
    ]

    # and it plays out to a champion from that bracket, not a re-drawn one
    c = playKnockout(ev, sport, sl)
    assert "Champion" in ev.results()[c.matchdays() - 1]


def test_rearranging_the_bracket_supersedes_a_stored_draw(sport_index, rng):
    """A draw only describes the tournament while the bracket still matches it."""
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    playKnockout(ev, sport, sl, upTo=1)
    assert ev.competitionOptions()["bracketResults"]

    # reverse the entrants, as dragging them around would
    reversed_ = list(reversed(ev.groups()[0].athletes))
    ev.setGroups([XkorGroup("Bracket", reversed_)])
    c = newKnockout(ev, sport, ev.makeStartList(XkorRPList()))

    fixtures = c._fixtures(0)
    names = [h.name for h, a in fixtures]
    assert names[0] != "Athlete 1"  # the old draw is not being reused
    assert c._rowsForRound(0) == {}  # nor are the results it produced


def test_an_unchanged_bracket_keeps_its_draw_and_results(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    playKnockout(ev, sport, sl, upTo=1)

    c = newKnockout(ev, sport, sl)
    assert len(c._rowsForRound(0)) == 4
    assert c._winnersOfRound(0) is not None


H2H_PARADIGM_SPORTS = [
    "eSports—Best of 5",       # XkorWrestlingParadigm
    "eSports—FPS—3 Match",     # XkorTennisParadigm
    "Judo—xkoranate formula",  # XkorBestOfParadigm
    "Fencing—Individual epee",  # XkorFencingParadigm
]


@pytest.mark.parametrize("sportName", H2H_PARADIGM_SPORTS)
def test_head_to_head_paradigms_all_offer_a_knockout(sport_index, rng, sportName):
    """These four subclass XkorAbstractParadigm rather than the H2H base, so
    declaring singleElimination on that base never reached them."""
    sport = XkorXmlSportReader(sport_index.lookup(sportName)).sport()
    paradigm = XkorParadigmFactory.newParadigmForSport(sport, {})
    assert paradigm.supportsCompetition("roundRobin")
    assert paradigm.supportsCompetition("singleElimination")


def test_every_paradigm_that_runs_matches_offers_a_knockout(sport_index):
    """The support rule, rather than a list of paradigms to keep in step.

    singleElimination used to be declared by hand in five places, and the
    first extension already diverged: archery and parallel giant slalom both
    run individual matches — everything a bracket needs — and neither was
    offered one.
    """
    seen = set()
    missing = []
    for name in sport_index.index:
        try:
            sport = XkorXmlSportReader(sport_index.lookup(name)).sport()
            paradigm = XkorParadigmFactory.newParadigmForSport(sport, {})
        except Exception:
            continue
        if type(paradigm).__name__ in seen:
            continue
        seen.add(type(paradigm).__name__)
        if paradigm.supportsCompetition("matches") \
                and not paradigm.supportsCompetition("singleElimination"):
            missing.append(type(paradigm).__name__)
    assert seen  # the sweep actually found paradigms
    assert missing == []


@pytest.mark.parametrize("sportName", H2H_PARADIGM_SPORTS)
def test_a_knockout_plays_out_for_every_head_to_head_paradigm(sport_index, rng, sportName):
    ev, sport, sl = buildKnockout(sport_index, rng, 8, sportName=sportName)
    c = playKnockout(ev, sport, sl)
    assert len(c._winnersOfRound(c._rounds() - 1)) == 1


def test_the_editor_never_shows_a_type_the_event_will_not_use(editor, sport_index, rng):
    """A saved type the sport's paradigm can't run used to leave the selector
    and the event disagreeing, so the editor said "round robin" while a cup
    was what actually got scorinated."""
    ev, sport = build_event(sport_index, rng, "Athletics—Men’s 00100 m—Round 1")
    ev.setCompetition("singleElimination")  # a sprint has no knockout

    editor.showEventEditor(ev)
    assert selectedCompetition(editor) == editor.ee.m_data.competition()
    assert selectedCompetition(editor) != "singleElimination"

    editor.updateCurrentEvent()
    assert ev.competition() == selectedCompetition(editor)


def test_resizing_the_bracket_clears_results_that_no_longer_apply(sport_index, rng):
    """Results from a bracket that has since been changed were still shown."""
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    playKnockout(ev, sport, sl, upTo=2)
    assert newKnockout(ev, sport, sl).results(0).strip()

    # cut the field down: the played rounds describe a bracket that is gone
    ev.setGroups([XkorGroup("Bracket", ev.groups()[0].athletes[:4])])
    c = newKnockout(ev, sport, ev.makeStartList(XkorRPList()))
    assert [c.results(i).strip() for i in range(3)] == ["", "", ""]


def test_toggling_the_playoff_clears_results_stored_under_the_old_numbering(sport_index, rng):
    """The playoff sits before the final, so enabling it shifts every later
    round along one and the final's result ends up under its heading."""
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    c = playKnockout(ev, sport, sl)
    assert c.matchdays() == 3
    assert c.results(2).strip()  # the final

    options = dict(ev.competitionOptions())
    options["thirdPlacePlayoff"] = "true"
    ev.setCompetitionOptions(options)

    c = newKnockout(ev, sport, sl)
    assert c.matchdays() == 4
    assert [c.results(i).strip() for i in range(4)] == ["", "", "", ""]


def test_a_bracket_too_small_to_play_says_so(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 1)
    c = newKnockout(ev, sport, sl)

    assert c.matchdays() == 0
    schedule = c.schedule()
    assert schedule is not None  # not "this type has no schedule to preview"
    assert "at least two participants" in schedule


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or XkorApplication(sys.argv)
    QDir.setSearchPaths("sports", [sportsDir()])
    return app


@pytest.mark.parametrize("sportName", [
    # paradigms that don't use a maximum skill: loading one used to re-check
    # the "pin to max participant" box mid-rebuild, whose dataChanged wrote
    # the momentarily-empty editor state back over the event being loaded
    "Basketball—xkoranate formula",
    "Association football—SQIS formula",
    # a paradigm that does use a maximum skill, as a control
    "Association football—NSFS formula",
])
def test_loading_saved_event_keeps_participants(qt_app, sport_index, rng, tmp_path, sportName):
    ev, _ = build_event(sport_index, rng, sportName)
    ev.setResult(0, "some result text")

    xmlPath = str(tmp_path / "event.xml")
    XkorXmlWriter(xmlPath, XkorRPList(), [(uuid.uuid4(), ev)])
    loaded = XkorXmlReader(xmlPath).events()[0][1]

    editor = XkorEventEditor()
    editor.loadSports()
    editor.setData(loaded, XkorRPList())

    data = editor.data()
    assert [a.name for a in data.signupList().athletes()] == \
        [a.name for a in ev.signupList().athletes()]
    assert data.results()[0] == "some result text"
    assert [g.athletes for g in data.groups()] == [g.athletes for g in ev.groups()]


# ----------------------------------------------- odds, stoppages, coin tosses


class _StubParadigm:
    """Just enough paradigm for _decideMatch: results it is told to return."""

    def __init__(self, results):
        self._results = results  # {athlete id: XkorResult}
        self.brokeTie = False

    def findResult(self, id):
        return self._results[id]

    def compare(self, a, b):
        if a.score() == b.score():
            return 0
        return 1 if a.score() > b.score() else -1

    def breakTie(self, athletes, type=""):
        self.brokeTie = True

    def option(self, key):
        return []


def _result(athlete, score, **values):
    from xkoranate.result import XkorResult

    r = XkorResult(score, ath=athlete)
    for k, v in values.items():
        r.result[k] = v
    return r


def test_a_stoppage_names_the_beaten_side(sport_index, rng):
    """A status on one side means that side was beaten, so the assignment is
    deliberately inverted — and an inverted-back version would advance the
    wrong athlete while every structural assertion still held."""
    ev, sport, sl = buildKnockout(sport_index, rng, 4)
    c = newKnockout(ev, sport, sl)
    home, away = sl.groups[0].athletes[0], sl.groups[0].athletes[1]

    p = _StubParadigm({home.id: _result(home, 0.0, status="ret."),
                       away.id: _result(away, 0.0)})
    _, _, _, winner = c._decideMatch(p, home, away)
    assert winner is away

    p = _StubParadigm({home.id: _result(home, 0.0),
                       away.id: _result(away, 0.0, status="ret.")})
    _, _, _, winner = c._decideMatch(p, home, away)
    assert winner is home


def test_a_match_the_paradigm_cannot_separate_is_flipped_for(sport_index, rng):
    """A knockout cannot end level; the coin toss is the last resort."""
    ev, sport, sl = buildKnockout(sport_index, rng, 4)
    c = newKnockout(ev, sport, sl)
    home, away = sl.groups[0].athletes[0], sl.groups[0].athletes[1]

    seen = set()
    for _ in range(50):
        p = _StubParadigm({home.id: _result(home, 1.0), away.id: _result(away, 1.0)})
        value1, value2, decider, winner = c._decideMatch(p, home, away)
        assert p.brokeTie  # the tiebreak path runs whatever allowDraws says
        assert decider == "coin toss"
        assert winner in (home, away)
        seen.add(winner.name)
    assert len(seen) == 2  # both sides come up


def test_a_coin_toss_is_reproducible_from_the_event_seed(sport_index, rng):
    """Everything else in a scorination replays from the seed; this did not."""
    def champion(seed):
        ev, sport, sl = buildKnockout(sport_index, Mt19937(seed), 4)
        sport.setPRNG(Mt19937(seed))
        c = playKnockout(ev, sport, sl)
        return c._winnersOfRound(c._rounds() - 1)[0].name

    assert champion(99) == champion(99)


def test_match_odds_cover_byes_normal_pairings_and_the_playoff(sport_index, rng):
    ev, sport, sl = buildKnockout(sport_index, rng, 6, {"thirdPlacePlayoff": "true"})
    c = newKnockout(ev, sport, sl)
    assert c.supportsOdds()

    first = c.matchOdds(0, trials=20)  # 6 entrants in an 8-slot bracket
    assert first is not None
    assert "BYE" in first

    # the playoff is its own matchday, and has no contestants until the
    # semi-finals have been played
    playoffMatchday = c.matchdays() - 2
    assert c.matchOdds(playoffMatchday, trials=20) is None

    c = playKnockout(ev, sport, sl, upTo=2)
    odds = c.matchOdds(playoffMatchday, trials=20)
    assert odds is not None and odds.strip()


def test_a_coin_toss_without_a_prng_is_still_reproducible(sport_index, rng, capsys):
    """A sport with no PRNG is a misconfiguration, but it must not make the
    one result the paradigm can't derive clock-dependent too."""
    ev, sport, sl = buildKnockout(sport_index, rng, 4)
    c = newKnockout(ev, sport, sl)
    c.sport.r = None

    flips = [c._coinFlip() for _ in range(8)]
    c2 = newKnockout(ev, sport, sl)
    c2.sport.r = None
    assert [c2._coinFlip() for _ in range(8)] == flips
    assert "no PRNG set" in capsys.readouterr().err


def test_scorinating_a_round_out_of_order_says_why_it_is_empty(sport_index, rng):
    """Leaving resultsBuf unset gave a blank matchday with no explanation,
    where the third-place playoff writes a line for the same situation."""
    ev, sport, sl = buildKnockout(sport_index, rng, 8)
    c = newKnockout(ev, sport, sl)

    c.scorinate(2)  # the final, with the earlier rounds unplayed
    result = c.results(2)
    assert "hasn't been played yet" in result
    assert c.matchdayNames()[2] in result


def test_switching_away_from_a_knockout_adds_no_stray_group(editor, sport_index, rng):
    """Leaving a knockout used to plant its empty bracket in the next event.

    Loading an event first empties the editor while it is still in the old
    event's bracket mode, so the setup page read back one empty pooled group.
    The switch to the next event's format then turned that into a group of
    its own, and a stray "Bracket" heading turned up in that event's results.
    """
    race, _ = build_event(sport_index, rng, "Athletics—Men’s 00100 m—Round 1")
    race.m_groups[0].name = "Final"
    cup, _ = build_event(sport_index, rng, "Association football—LISA formula")
    cup.setCompetition("singleElimination")

    def groups():
        return [(g.name, len(g.athletes)) for g in editor.ee.eventSetupWidget.groups()]

    editor.showEventEditor(race)
    assert groups() == [("Final", 8)]

    editor.showEventEditor(cup)
    for _ in range(3):
        editor.ee.goNext()  # through to the scorinate page

    editor.showEventEditor(race)
    assert groups() == [("Final", 8)]
    editor.updateCurrentEvent()
    assert [g.name for g in race.groups()] == ["Final"]


def test_an_empty_group_survives_a_trip_through_the_knockout_format(editor):
    """An empty bracket carries nothing over, but the pools it replaced still come back."""
    from xkoranate.eventeditor.eventsetupwidget import XkorEventSetupWidget

    w = XkorEventSetupWidget()
    w.setCompetition("roundRobin")
    w.setGroups([XkorGroup("Group 1", [])])
    w.setCompetition("singleElimination")
    w.setCompetition("roundRobin")
    assert [(g.name, g.athletes) for g in w.groups()] == [("Group 1", [])]

    # with nothing remembered, an empty bracket leaves nothing behind
    w.reset()
    w.setCompetition("singleElimination")
    w.setGroups([])
    w.setCompetition("roundRobin")
    assert w.groups() == []


# ------------------------------------------------------ stoppages in tables


@pytest.mark.parametrize("sportName", ["Boxing—xkoranate formula", "Taekwondo—xkoranate formula"])
def test_a_stoppage_counts_as_a_win_for_the_winner_in_a_league_table(sport_index, sportName):
    """A KO, DSQ and the like used to go into the table as the largest
    float the wrong way round: the beaten side was credited the win, and
    the goal difference overflowed to infinity and crashed the table."""
    import re

    stoppages = 0
    for seed in range(6):
        ev, sport = build_event(sport_index, Mt19937(seed), sportName)
        ev.setCompetition("roundRobin")
        sl = ev.makeStartList(XkorRPList())
        opts = {"numberOfLegs": "2"}
        results = {}

        def build():
            return XkorCompetitionFactory.newCompetitionFull(
                "roundRobin", sl, sport, ev.paradigmOptions(), opts, results)

        c = build()
        for md in range(c.matchdays()):
            c.scorinate(md)  # used to raise OverflowError on a stoppage
            results[md] = c.results(md)
            opts.update(c.resumeFileOptions())
            c = build()

        stored = {}
        for line in opts["tableData"][0]:
            # taekwondo scores can go below zero
            rx = re.match(r"(\d+): (.+) (-?[0-9.]+)–(-?[0-9.]+) (.+)", line)
            assert rx, line
            stored[(int(rx.group(1)), rx.group(2), rx.group(5))] = (float(rx.group(3)), float(rx.group(4)))

        for md, text in results.items():
            for rx in re.finditer(r"^(.+?) \(\w+\) def\.( by)? (.+?) \(\w+\) \((\w+)\)$", text, re.M):
                home, by, away = rx.group(1), rx.group(2), rx.group(3)
                h, a = stored[(md, home, away)]
                assert (h < a) if by else (h > a), rx.group(0)
                stoppages += 1
    assert stoppages > 0  # the seeds actually produced some


# ------------------------------------------------------ unbreakable shoot-offs

NO_SHOOTOFF_DATA = [
    "Shooting—Mixed team 10 m air pistol—Qualification",
    "Shooting—Mixed team 10 m air pistol—Final (Last series)",
    "Shooting—Mixed team 10 m air pistol—Final (First six series)",
    "Shooting—Mixed team 10 m air rifle—Qualification",
    "Shooting—Mixed team 10 m air rifle—Final (Last series)",
    "Shooting—Mixed team 10 m air rifle—Final (First six series)",
    "Shooting—Mixed team trap—Final",
]


@pytest.mark.parametrize("sportName", NO_SHOOTOFF_DATA)
def test_a_tie_that_no_shoot_off_can_break_stands_instead_of_hanging(sport_index, capfd, sportName):
    """These sports have no shoot-off data, so every shoot-off shot scored the
    same and a tie at the cutoff or on the podium re-shot forever."""
    import signal

    def hang(signum, frame):
        raise AssertionError("scorination never finished")

    old = signal.signal(signal.SIGALRM, hang)
    try:
        for seed in [6450, 6510] + list(range(40)):
            ev, sport = build_event(sport_index, Mt19937(seed), sportName)
            athletes = list(ev.groups()[0].athletes)
            ev.setGroups([XkorGroup("Group A", athletes[:4]), XkorGroup("Group B", athletes[4:])])
            ev.setCompetition("shooting")
            sl = ev.makeStartList(XkorRPList())
            opts, results = {}, {}
            for md in range(2):
                c = XkorCompetitionFactory.newCompetitionFull(
                    "shooting", sl, sport, ev.paradigmOptions(), opts, results)
                signal.alarm(10)
                c.scorinate(md)
                signal.alarm(0)
                results[md] = c.results(md)
                opts.update(c.resumeFileOptions())
                assert results[md].strip()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
    # the seeds did produce a tie the sport couldn't break
    assert "can't break a tie by shoot-off" in capfd.readouterr().err


# --- qualification markers (Q / E) -------------------------------------------

def playGroups(index, rng, sportName, competition, groups, perGroup):
    """Scorinate every matchday, rebuilding the competition from the saved
    options in between the way the Scorinate step does."""
    ev, sport = build_event(index, rng, sportName, groups * perGroup)
    ids = list(ev.groups()[0].athletes)
    ev.setGroups([XkorGroup("Group %s" % chr(65 + g), ids[g * perGroup:(g + 1) * perGroup])
                  for g in range(groups)])
    ev.setCompetition(competition)
    sl = ev.makeStartList(XkorRPList())

    def build():
        return XkorCompetitionFactory.newCompetitionFull(
            competition, sl, sport, ev.paradigmOptions(), ev.competitionOptions(), ev.results())

    c = build()
    for md in range(c.matchdays()):
        c.scorinate(md)
        ev.replaceCompetitionOptions(c.resumeFileOptions())
        ev.setResult(md, c.results(md))
        c = build()
    return ev, sport, c


def markerCounts(text):
    rows = [line for line in text.split("\n") if line[-2:] in (" Q", " E")]
    return sum(1 for r in rows if r.endswith("Q")), sum(1 for r in rows if r.endswith("E"))


def test_league_markers_on_the_final_matchday(sport_index, rng):
    from xkoranate.competitions.qualification import QualificationSettings

    ev, sport, c = playGroups(sport_index, rng, "Association football—SQIS formula",
                              "roundRobin", 3, 4)
    last = c.matchdays() - 1
    text = c.results(last)

    assert c.formatQualifications(text, last, QualificationSettings()) == text
    assert markerCounts(c.formatQualifications(text, last, QualificationSettings("top", 2))) == (6, 6)
    assert markerCounts(c.formatQualifications(
        text, last, QualificationSettings("topPlusBest", 2, 1))) == (7, 5)
    # after one game nobody is through or out yet
    assert c.formatQualifications(c.results(0), 0, QualificationSettings("top", 2)) == c.results(0)


def test_league_markers_survive_a_save_and_reload(sport_index, rng, tmp_path):
    from xkoranate.competitions.qualification import QualificationSettings

    ev, sport, c = playGroups(sport_index, rng, "Association football—SQIS formula",
                              "roundRobin", 2, 4)
    ev.replaceCompetitionOptions(QualificationSettings("top", 2).toOptions())
    xmlPath = str(tmp_path / "league.xml")
    XkorXmlWriter(xmlPath, XkorRPList(), [(uuid.uuid4(), ev)])
    ev2 = XkorXmlReader(xmlPath).events()[0][1]

    settings = QualificationSettings.fromOptions(ev2.competitionOptions())
    assert settings == QualificationSettings("top", 2)
    c2 = XkorCompetitionFactory.newCompetitionFull(
        "roundRobin", ev2.makeStartList(XkorRPList()), sport, ev2.paradigmOptions(),
        ev2.competitionOptions(), ev2.results())
    last = c2.matchdays() - 1
    assert markerCounts(c2.formatQualifications(c2.results(last), last, settings)) == (4, 4)


def test_heat_markers_with_the_best_next_placed(sport_index, rng):
    from xkoranate.competitions.qualification import QualificationSettings

    ev, sport, c = playGroups(sport_index, rng, "Athletics—Men’s 00100 m—Round 1",
                              "standard", 3, 5)
    assert len(ev.competitionOptions()["heatRanks"]) == 3
    text = c.results(0)
    best = QualificationSettings("topPlusBest", 2, 1)
    assert markerCounts(c.formatQualifications(text, 0, QualificationSettings("top", 2))) == (6, 9)
    assert markerCounts(c.formatQualifications(text, 0, best)) == (7, 8)

    # saved before heat ranks were kept: the third-placed can't be compared
    old = dict(ev.competitionOptions())
    del old["heatRanks"]
    c = XkorCompetitionFactory.newCompetitionFull(
        "standard", ev.makeStartList(XkorRPList()), sport, ev.paradigmOptions(), old, ev.results())
    assert markerCounts(c.formatQualifications(text, 0, best)) == (6, 6)


def test_scorinate_step_box_loads_quietly_and_saves_changes(qt_app, sport_index, rng):
    from xkoranate.competitions.qualification import QualificationSettings
    from xkoranate.eventeditor.scorinatewidget import XkorScorinateWidget

    ev, sport, c = playGroups(sport_index, rng, "Association football—SQIS formula",
                              "roundRobin", 3, 4)
    ev.replaceCompetitionOptions(QualificationSettings("topPlusBest", 2, 1).toOptions())

    w = XkorScorinateWidget()
    saved = []
    w.resumeFileOptionsSet.connect(saved.append)
    w.setEvent(ev, XkorRPList(), sport)
    assert saved == []  # opening an event doesn't mark it changed
    assert not w.qualificationBox.isHidden()
    assert w.qualificationSettings() == QualificationSettings("topPlusBest", 2, 1)

    w.matchday.setCurrentIndex(w.matchday.count() - 1)
    assert markerCounts(w.textedit.toPlainText()) == (7, 5)

    w.qualificationBest.setChecked(False)
    assert saved[-1]["qualificationMode"] == "top"
    assert markerCounts(w.textedit.toPlainText()) == (6, 6)

    w.qualificationBox.setChecked(False)
    assert saved[-1]["qualificationMode"] == "off"
    assert w.textedit.toPlainText() == c.results(c.matchdays() - 1)


# --- events saved before qualification markers existed -----------------------
# Written by the code on main before this feature: no qualification options,
# no heat ranks, coin flips not saved. Clicking the box on them must not crash.

PRE_QUALIFICATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "fixtures", "pre-qualification")
PRE_QUALIFICATION_FILES = sorted(f for f in os.listdir(PRE_QUALIFICATION) if f.endswith(".xml"))


def clickEveryQualificationSetting(w):
    """Every mode, on every matchday, with and without BBCode."""
    for checked, best, places, bestOf in [(True, False, 1, 1), (True, True, 2, 1),
                                          (True, True, 1, 3), (True, False, 99, 1),
                                          (False, False, 2, 1)]:
        w.qualificationPlaces.setValue(places)
        w.qualificationBestOf.setValue(bestOf)
        w.qualificationBest.setChecked(best)
        w.qualificationBox.setChecked(checked)
        for md in range(max(1, w.matchday.count())):
            w.matchday.setCurrentIndex(md)
            w.updateResults(md)
        w.bbcodeCheckBox.toggle()


def openInEditor(editor, path, damage=None):
    r = XkorXmlReader(path)
    ev = r.events()[0][1]
    if damage is not None:
        damage(ev.m_competitionOptions)
    editor.ee.setData(ev, r.rpList())
    return editor.ee.scorinateWidget


@pytest.mark.parametrize("name", PRE_QUALIFICATION_FILES)
def test_old_files_take_every_qualification_setting(editor, name, capfd):
    w = openInEditor(editor, os.path.join(PRE_QUALIFICATION, name))
    clickEveryQualificationSetting(w)
    assert "Traceback" not in capfd.readouterr().err

    # and where there are finished standings, they get marked
    if name.startswith("rr-") and "not-started" not in name and "halfway" not in name:
        w.qualificationPlaces.setValue(2)
        w.qualificationBest.setChecked(False)
        w.qualificationBox.setChecked(True)
        w.matchday.setCurrentIndex(w.matchday.count() - 1)
        rows = w.textedit.toPlainText().split("\n")
        # a Q in the marker column: at the end, or before a results grid
        assert any(line.endswith(" Q") or " Q  " in line for line in rows)


def damagedOptions():
    def junkSettings(o):
        o.update(qualificationMode="banana", qualificationPlaces="abc", qualificationBestOf="-7")

    def hugeSettings(o):
        o.update(qualificationMode="topPlusBest", qualificationPlaces="99999", qualificationBestOf="0")

    def junkTableData(o):
        td = list(o.get("tableData") or [[]])
        td[0] = list(td[0]) + ["garbage", "99: Nobody 1–0 Ghost", "x: A 1–1 B"]
        o["tableData"] = td + [["0: Extra 1–0 Group"]]

    def tableDataNotAList(o):
        o["tableData"] = "not a list"

    def junkHeatRanks(o):
        o["heatRanks"] = [["x", "", "3"], "nonsense", [], ["1"] * 99]

    def heatRanksNotAList(o):
        o["heatRanks"] = "7"

    return [junkSettings, hugeSettings, junkTableData, tableDataNotAList,
            junkHeatRanks, heatRanksNotAList]


@pytest.mark.parametrize("damage", damagedOptions(), ids=lambda f: f.__name__)
@pytest.mark.parametrize("name", ["rr-groups-halfway.xml", "rr-coinflip-wins.xml", "ms-heats.xml"])
def test_hand_damaged_options_dont_crash_the_box(editor, name, damage, capfd):
    w = openInEditor(editor, os.path.join(PRE_QUALIFICATION, name), damage)
    clickEveryQualificationSetting(w)
    assert "Traceback" not in capfd.readouterr().err


def test_coin_flip_ties_in_an_old_league_still_get_marked(editor):
    # league tables never saved their flips; the markers take them from the
    # order the stored table shows rather than re-rolling (and missing it)
    for _ in range(5):
        w = openInEditor(editor, os.path.join(PRE_QUALIFICATION, "rr-coinflip-wins.xml"))
        w.qualificationPlaces.setValue(2)
        w.qualificationBest.setChecked(False)
        w.qualificationBox.setChecked(True)
        w.matchday.setCurrentIndex(w.matchday.count() - 1)
        assert markerCounts(w.textedit.toPlainText()) == (4, 4)


def test_a_formatting_failure_shows_the_results_plain(editor, capfd):
    w = openInEditor(editor, os.path.join(PRE_QUALIFICATION, "rr-one-group-done.xml"))

    def broken(*args):
        raise RuntimeError("something an old file confused")

    w.c.formatQualifications = broken
    w.qualificationBox.setChecked(True)
    md = w.matchday.currentIndex()
    assert w.textedit.toPlainText() == w.c.results(md)
    assert "something an old file confused" in capfd.readouterr().err
