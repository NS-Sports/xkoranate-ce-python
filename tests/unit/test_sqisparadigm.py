from paradigm_helpers import make_paradigm, make_sport, stub_uniform

from xkoranate.paradigms.sqisparadigm import XkorSQISParadigm


def test_generateScore_equal_skills_uses_constantA_as_goal_probability(monkeypatch):
    sport = make_sport(seed=1)
    p = make_paradigm(XkorSQISParadigm, opts={"attacks": 1, "constantA": 0.5, "constantB": 0.3}, sport=sport)

    stub_uniform(monkeypatch, sport, [0.0])
    assert p.generateScore(0.5, 0.5, 0, 0) == 0

    stub_uniform(monkeypatch, sport, [0.9])
    assert p.generateScore(0.5, 0.5, 0, 0) == 1


def test_generateScore_favourite_scores_more_often_than_underdog(monkeypatch):
    sport = make_sport(seed=1)
    p = make_paradigm(XkorSQISParadigm, opts={"attacks": 10, "constantA": 0.1, "constantB": 0.2}, sport=sport)

    fixed_rand = 0.5
    stub_uniform(monkeypatch, sport, [fixed_rand])
    favourite = p.generateScore(0.9, 0.1, 0, 0)

    stub_uniform(monkeypatch, sport, [fixed_rand])
    underdog = p.generateScore(0.1, 0.9, 0, 0)

    assert favourite > underdog


def test_generateScore_home_advantage_increases_goal_probability(monkeypatch):
    sport = make_sport(seed=1)
    p = make_paradigm(XkorSQISParadigm,
                       opts={"attacks": 10, "constantA": 0.1, "constantB": 0.2, "homeAdvantage": 2.0},
                       sport=sport)

    fixed_rand = 0.5
    stub_uniform(monkeypatch, sport, [fixed_rand])
    without_advantage = p.generateScore(0.5, 0.5, 0, 0, homeAdvantage=False)

    stub_uniform(monkeypatch, sport, [fixed_rand])
    with_advantage = p.generateScore(0.5, 0.5, 0, 0, homeAdvantage=True)

    assert with_advantage >= without_advantage
