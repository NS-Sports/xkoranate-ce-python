import random
import uuid

import pytest
from builders import (make_athlete, make_athletes, make_event, make_paradigm, make_signup_list,
                      make_sport, new_competition)

from xkoranate.paradigms.h2hparadigm import XkorH2HParadigm
from xkoranate.paradigms.nsfsbaseballparadigm import XkorNSFSBaseballParadigm
from xkoranate.result import XkorResult
from xkoranate.rng import Mt19937
from xkoranate.rplist import XkorRPList
from xkoranate.variant import toList
from xkoranate.xml.xmlsportreader import XkorXmlSportReader

BASEBALL = "Baseball—Adjusted NSFS3 formula"
ADJUSTED = {"baseScoringProb": 0.2815, "baseScoringCoeff": 0.09,
            "extraScoringProb": 0.4095, "extraScoringCoeff": 0.09}


def scores(skill, oppSkill):
    p = make_paradigm(XkorNSFSBaseballParadigm, opts=ADJUSTED, sport=make_sport(seed=1))
    return [p.generateScorePair(skill, oppSkill) for _ in range(50)]


def test_a_gap_wider_than_the_skill_scale_plays_as_the_widest_gap():
    # was an OverflowError: the gap of 21 put the run multiplier near 2
    assert scores(91.0, 70.0) == scores(1.0, 0.0)


def test_a_gap_on_the_skill_scale_is_unchanged():
    assert scores(0.91, 0.42) != scores(1.0, 0.0)


def test_match_odds_survive_skills_that_were_never_scaled(sport_index):
    """What a new event did after an import, before the import lifted the
    maximum skill: 91 against 70 in a round robin, on a 0-1 scale."""
    athletes = make_athletes(8, skills=[91, 84, 77, 70, 63, 56, 49, 42])
    sport = XkorXmlSportReader(sport_index.lookup(BASEBALL)).sport()
    sport.setPRNG(Mt19937(2026))
    ev = make_event(athletes, groups=[4, 4], sport=BASEBALL, paradigm=sport.paradigm(),
                    competition="roundRobin")
    ev.setSignupList(make_signup_list(athletes, 0, 1))
    c = new_competition(ev, sport, ev.makeStartList(XkorRPList()))

    assert "%" in c.matchOdds(0, trials=50)


# --- walk-offs ----------------------------------------------------------------
# The game ends the moment the home side (listed second, batting last) goes
# ahead in its last turn at bat, so it can win that way by 4 at most: a grand
# slam with the scores level.

NINE = dict(ADJUSTED, periods=9)
BASEBALL_FILES = ["Baseball—NSFS3 formula", "Baseball—Adjusted NSFS3 formula",
                  "Baseball—LLWS formula", "Baseball—xkoranate formula",
                  "Softball—xkoranate formula"]


def innings(monkeypatch, paradigm, pairs):
    """Feed generateScorePair (home runs, visitor runs) pairs in order."""
    it = iter(pairs)
    monkeypatch.setattr(paradigm, "generateScorePair",
                        lambda skill, oppSkill, attackMultiplier=1: next(it))


def baseball(user_opts=None):
    return make_paradigm(XkorNSFSBaseballParadigm, opts=NINE, user_opts=user_opts,
                         sport=make_sport(seed=1))


def test_a_ninth_inning_rally_stops_four_runs_ahead(monkeypatch):
    p = baseball()
    # level at 1-1 after eight; the home side's 7 in the ninth becomes 4
    innings(monkeypatch, p, [(1, 1)] + [(0, 0)] * 7 + [(7, 0)])
    visitor, home = p.generateFTScore(make_athlete("V"), make_athlete("H"))
    assert (visitor.score(), home.score()) == (1, 5)
    assert toList(home.result["subScores"])[-1] == 4


def test_a_ninth_inning_rally_from_behind_keeps_the_runs_it_needed(monkeypatch):
    p = baseball()
    # 3 behind going into the bottom of the ninth: 9 runs becomes 3 + 4
    innings(monkeypatch, p, [(0, 3)] + [(0, 0)] * 7 + [(9, 0)])
    visitor, home = p.generateFTScore(make_athlete("V"), make_athlete("H"))
    assert (visitor.score(), home.score()) == (3, 7)


def test_a_ninth_inning_that_falls_short_is_untouched(monkeypatch):
    p = baseball()
    innings(monkeypatch, p, [(0, 5)] + [(0, 0)] * 7 + [(3, 0)])
    visitor, home = p.generateFTScore(make_athlete("V"), make_athlete("H"))
    assert (visitor.score(), home.score()) == (5, 3)


def test_the_home_side_skips_the_ninth_when_already_ahead(monkeypatch):
    p = baseball()
    innings(monkeypatch, p, [(2, 0)] + [(0, 0)] * 7 + [(6, 1)])
    visitor, home = p.generateFTScore(make_athlete("V"), make_athlete("H"))
    assert (visitor.score(), home.score()) == (1, 2)
    assert len(toList(home.result["subScores"])) == 8


def test_without_line_scores_the_ninth_still_stops_four_ahead(monkeypatch):
    p = baseball({"usePeriods": "false"})
    # eight innings 2-2, then the home side scores 8 in the ninth
    innings(monkeypatch, p, [(2, 2), (8, 0)])
    visitor, home = p.generateFTScore(make_athlete("V"), make_athlete("H"))
    assert (visitor.score(), home.score()) == (2, 6)


def extra_inning(monkeypatch, pair):
    p = baseball()
    innings(monkeypatch, p, [pair])
    visitor, home = XkorResult(), XkorResult()
    visitor.athlete, home.athlete = make_athlete("V"), make_athlete("H")
    visitor.setScore(3)
    home.setScore(3)
    return p.generateETScore(visitor, home)


def test_an_extra_inning_walk_off_stops_four_runs_ahead(monkeypatch):
    # extras hand generateScorePair the visitor first, so the pair comes
    # back (visitor runs, home runs): 1 behind, the home side keeps 1 + 4
    visitor, home = extra_inning(monkeypatch, (1, 8))
    assert (visitor.score(), home.score()) == (4, 8)
    assert toList(home.result["subScores"]) == [5]


def test_an_extra_inning_won_by_the_visitor_is_untouched(monkeypatch):
    visitor, home = extra_inning(monkeypatch, (7, 0))
    assert (visitor.score(), home.score()) == (10, 3)


def test_extra_innings_play_on_the_rp_adjusted_skill(monkeypatch):
    p = baseball()
    seen = []
    monkeypatch.setattr(p, "generateScorePair",
                        lambda skill, oppSkill, attackMultiplier=1:
                        seen.append((skill, oppSkill)) or (1, 0))
    visitor, home = XkorResult(), XkorResult()
    visitor.athlete = make_athlete("V", skill=0.2, rp_skill=0.6)
    home.athlete = make_athlete("H", skill=0.3, rp_skill=0.7)
    p.generateETScore(visitor, home)
    assert seen == [(0.6, 0.7)]


def h2h_extra_time(monkeypatch, opts, runs):
    sport = make_sport(seed=1)
    it = iter(runs)
    monkeypatch.setattr(sport, "h2hScore", lambda index, skill, oppSkill: next(it))
    p = make_paradigm(XkorH2HParadigm, opts=opts, sport=sport)
    first, second = XkorResult(), XkorResult()
    first.athlete, second.athlete = make_athlete("A"), make_athlete("B")
    first.setScore(2)
    second.setScore(2)
    return p.generateETScore(first, second, "")


def test_xkoranate_formula_extra_innings_stop_the_side_batting_last_four_ahead(monkeypatch):
    first, second = h2h_extra_time(monkeypatch, {"walkOffMargin": 4}, [0, 5])
    assert (first.score(), second.score()) == (2, 6)


def test_xkoranate_formula_extra_innings_leave_the_side_batting_first_alone(monkeypatch):
    first, second = h2h_extra_time(monkeypatch, {"walkOffMargin": 4}, [5, 0])
    assert (first.score(), second.score()) == (7, 2)


def test_sports_without_a_walk_off_keep_every_extra_time_goal(monkeypatch):
    first, second = h2h_extra_time(monkeypatch, {}, [0, 5])
    assert (first.score(), second.score()) == (2, 7)


def line_score_problems(visitor, home, periods):
    """What, if anything, makes a finished game impossible under baseball rules."""
    problems = []
    if visitor.score() == home.score():
        problems.append("tied")
    vs = [int(x) for x in toList(visitor.result.get("subScores"))]
    hs = [int(x) for x in toList(home.result.get("subScores"))]
    if not vs:
        return problems
    if sum(vs) != visitor.score() or sum(hs) != home.score():
        problems.append("innings don't add up")
    vt = ht = 0
    for i, runs in enumerate(vs):
        vt += runs
        last = i >= periods - 1
        if i >= len(hs):
            if not (last and ht > vt):
                problems.append("home skipped its turn without leading")
            continue
        if last and ht > vt:
            problems.append("home batted while ahead in the last inning")
        ht += hs[i]
        if last and ht - vt > 4:
            problems.append("walk-off by more than 4")
        if last and vt != ht and i < len(vs) - 1:
            problems.append("played on once the game was decided")
    return problems


@pytest.mark.parametrize("name", BASEBALL_FILES)
def test_every_baseball_formula_finishes_games_that_could_happen(sport_index, name):
    sport = XkorXmlSportReader(sport_index.lookup(name)).sport()
    sport.setPRNG(Mt19937(2026))
    p = make_paradigm(XkorNSFSBaseballParadigm if sport.paradigm() == "nsfs-baseball"
                      else XkorH2HParadigm, sport=sport)
    periods = int(p.opt.get("periods", 9))
    skills = random.Random(2026)
    walkOffs = 0
    for _ in range(3000):
        visitor = make_athlete("V", skill=skills.random(), athlete_id=uuid.uuid4())
        home = make_athlete("H", skill=skills.random(), athlete_id=uuid.uuid4())
        p.scorinate([visitor, home])
        first, second = p.res
        assert line_score_problems(first, second, periods) == [], p.out[0][1]
        walkOffs += second.score() > first.score()
    assert walkOffs > 0
