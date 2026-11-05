from builders import make_athletes, make_event, make_paradigm, make_signup_list, make_sport, new_competition

from xkoranate.paradigms.nsfsbaseballparadigm import XkorNSFSBaseballParadigm
from xkoranate.rng import Mt19937
from xkoranate.rplist import XkorRPList
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
