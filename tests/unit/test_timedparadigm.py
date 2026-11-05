import sys

import pytest
from builders import event_for, make_athlete, make_athletes, make_paradigm, new_competition, play

from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory
from xkoranate.paradigms.timedparadigm import XkorTimedParadigm
from xkoranate.result import XkorResult
from xkoranate.rng import Mt19937
from xkoranate.xml.xmlsportreader import XkorXmlSportReader

SHOT_PUT_FINAL = "Athletics—Men’s shot put—Round 2"
DECATHLON_100 = "Athletics—Men’s decathlon—Event 01"
FASTING = "Summer vigil fasting"

# the decathlon 100 m: 25.4347 × (18 − time)^1.81
HUNDRED_METRES = {"decathlonA": 25.4347, "decathlonB": 18, "decathlonC": 1.81,
                  "displayDigits": 2, "resultWidth": 5}


def points(p, score, scoreString=""):
    """The decathlon points at the end of a result's output line."""
    r = XkorResult(score, scoreString, make_athlete("A"))
    r.result["attemptStrings"] = [scoreString]
    return int(p.outputLine(r).split()[-1])


def test_decathlon_points_follow_the_scoring_table():
    p = make_paradigm(XkorTimedParadigm, opts=HUNDRED_METRES)

    assert points(p, 10.50, "10.50") == 973  # scored as 10.51: the time is rounded up first


def test_a_time_slower_than_b_scores_no_decathlon_points():
    p = make_paradigm(XkorTimedParadigm, opts=HUNDRED_METRES)

    assert points(p, 18.00, "18.00") == 0
    assert points(p, 21.73, "21.73") == 0  # was a math domain error


@pytest.mark.parametrize("sortOrder,failure", [("ascending", sys.float_info.max),
                                               ("descending", -sys.float_info.max)])
def test_a_failure_scores_no_decathlon_points(sortOrder, failure):
    p = make_paradigm(XkorTimedParadigm, opts=dict(HUNDRED_METRES, sortOrder=sortOrder))

    assert points(p, failure, "DNF") == 0  # was an overflow rounding the score


def test_a_failure_in_a_descending_sport_is_not_summed():
    p = make_paradigm(XkorTimedParadigm, opts={"sortOrder": "descending", "displayDigits": 2})
    r = XkorResult(ath=make_athlete("A"))
    r.result["attempts"] = [20.5, -sys.float_info.max]
    r.result["attemptStrings"] = ["20.50", "DNF"]

    p.calculateTotal(r)

    assert r.score() == -sys.float_info.max
    assert r.scoreString() == "DNF"


def test_a_field_event_final_of_fewer_than_eight_gives_everyone_further_attempts(sport_index):
    sport = XkorXmlSportReader(sport_index.lookup(SHOT_PUT_FINAL)).sport()
    sport.setPRNG(Mt19937(2026))
    p = XkorParadigmFactory.newParadigmForSport(sport, {})

    p.scorinate(make_athletes(6))  # was an IndexError: the cutoff is eight

    assert [len(r.value("attempts")) for r in p.results()] == [6] * 6


@pytest.mark.parametrize("sportName,competition", [
    (SHOT_PUT_FINAL, "standard"),
    (SHOT_PUT_FINAL, "multipleRun"),
    (DECATHLON_100, "multipleRun"),
    (FASTING, "standard"),
    (FASTING, "multipleRun"),
])
def test_sports_that_crashed_now_play_out(sport_index, sportName, competition):
    ev, sport = event_for(sport_index, Mt19937(2026), sportName, n=6, competition=competition)

    c = play(ev, sport)

    assert all(c.results(md).strip() for md in range(c.matchdays()))


def test_a_failure_in_a_descending_sport_leaves_a_multiple_run_competition(sport_index):
    ev, sport = event_for(sport_index, Mt19937(2026), FASTING, n=6, competition="multipleRun")
    c = new_competition(ev, sport)

    c.scorinate(0)

    options = c.resumeFileOptions()
    failed = [line for line in c.results(0).splitlines() if "DNF" in line or "DSQ" in line]
    assert failed  # half the field fails, on average
    assert len(options["disqualifiedAthletes"]) == len(failed)
    assert len(options["athletes"]) == 6 - len(failed)
