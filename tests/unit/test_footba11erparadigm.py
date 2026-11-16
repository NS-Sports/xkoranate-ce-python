from builders import make_athlete, make_paradigm, make_sport, stub_uniform

from xkoranate.paradigms.footba11erparadigm import XkorFootba11erParadigm
from xkoranate.result import XkorResult

SEVENS = {"pointValues": [7, 5], "pointProbs": [0.64, 0.36]}


def golden_point(monkeypatch, opts):
    sport = make_sport(seed=1)
    stub_uniform(monkeypatch, sport, [0.1, 0.0])  # a converted try, and it's the home side's
    p = make_paradigm(XkorFootba11erParadigm, opts=opts, sport=sport)
    home = XkorResult(ath=make_athlete(name="Home"))
    away = XkorResult(ath=make_athlete(name="Away"))
    home.result["subScores"] = [2, 1]
    away.result["subScores"] = [2, 1]
    return p.generateGGScore(home, away, "")


def test_a_golden_point_try_ends_the_game_before_its_conversion(monkeypatch):
    home, away = golden_point(monkeypatch, dict(SEVENS, goldenGoalPointValues=[5, 5]))
    assert home.value("score") == 5
    assert home.value("subScores") == [2, 2]  # counted as an unconverted try


def test_without_golden_point_values_a_score_keeps_its_regulation_worth(monkeypatch):
    home, away = golden_point(monkeypatch, SEVENS)
    assert home.value("score") == 7
    assert home.value("subScores") == [3, 1]
