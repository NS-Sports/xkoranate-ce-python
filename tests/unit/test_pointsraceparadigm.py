import sys

from paradigm_helpers import make_athlete, make_paradigm, make_sport

from xkoranate.paradigms.pointsraceparadigm import XkorPointsRaceParadigm


def test_scorinate_computes_points_and_laps_score(monkeypatch):
    sport = make_sport(seed=1)
    values = {"points": 5.0, "laps": 2.0}
    monkeypatch.setattr(sport, "individualScore", lambda index, skill=None: values[index])
    monkeypatch.setattr(sport, "randWeighted", lambda skill: 0.5)
    p = make_paradigm(XkorPointsRaceParadigm, opts={"maxPoints": 10}, sport=sport)
    athletes = [make_athlete(name="A"), make_athlete(name="B")]

    p.scorinate(athletes)

    assert len(p.res) == 2
    for r in p.res:
        assert r.value("points") == 5.0
        assert r.value("laps") == 2.0
        assert r.score() == 45.0  # curPoints(5) + curLaps(2) * 20


def test_scorinate_uses_laps_only_when_usePoints_is_false(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "individualScore", lambda index, skill=None: {"laps": 3.0}[index])
    monkeypatch.setattr(sport, "randWeighted", lambda skill: 0.5)
    p = make_paradigm(XkorPointsRaceParadigm, opts={"usePoints": "false"}, sport=sport)

    p.scorinate([make_athlete(name="A")])

    r = p.res[0]
    assert r.value("points") is None
    assert r.score() == 3.0


def test_scorinate_applies_dnf_status(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randUniform", lambda: 0.0)  # always triggers the only status
    values = {"points": 5.0, "laps": 2.0}
    monkeypatch.setattr(sport, "individualScore", lambda index, skill=None: values[index])
    monkeypatch.setattr(sport, "randWeighted", lambda skill: 0.5)
    p = make_paradigm(XkorPointsRaceParadigm,
                       opts={"maxPoints": 10, "statuses": ["DNF"], "statusProbs": [1.0]},
                       sport=sport)

    p.scorinate([make_athlete(name="A")])

    r = p.res[0]
    assert r.score() == -sys.float_info.max
    assert r.scoreString().strip() == "DNF"
