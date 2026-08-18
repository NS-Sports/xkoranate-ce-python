import pytest
from paradigm_helpers import make_athlete, make_paradigm, make_sport

from xkoranate.paradigms.ordinalparadigm import XkorOrdinalParadigm


def test_generateScore_defaults_to_randWeighted_when_no_attack_modifier(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randWeighted", lambda skill: 0.42)
    p = make_paradigm(XkorOrdinalParadigm, opts={}, sport=sport)

    assert p.generateScore(0.7) == pytest.approx(0.42)


def test_generateScore_blends_in_randUniform_when_attack_modifier_set(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randWeighted", lambda skill: 1.0)
    monkeypatch.setattr(sport, "randUniform", lambda: 0.0)
    p = make_paradigm(XkorOrdinalParadigm, opts={"attackModifier": 1.0}, sport=sport)

    assert p.generateScore(0.7) == pytest.approx(0.5)  # (1.0 + 1.0*0.0) / (1+1.0)


def test_scorinate_ranks_athletes_descending_by_score(monkeypatch):
    sport = make_sport(seed=1)
    scores = iter([0.2, 0.9, 0.5])
    monkeypatch.setattr(sport, "randWeighted", lambda skill: next(scores))
    p = make_paradigm(XkorOrdinalParadigm, opts={}, sport=sport)
    athletes = [make_athlete(name="A"), make_athlete(name="B"), make_athlete(name="C")]

    p.scorinate(athletes)

    assert [r.athlete.name for r in p.res] == ["B", "C", "A"]
    assert p.out[0][1].endswith("1")
    assert p.out[1][1].endswith("2")
    assert p.out[2][1].endswith("3")


def test_scorinate_applies_status_penalty_and_scoreString(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randUniform", lambda: 0.0)  # always triggers the only status
    monkeypatch.setattr(sport, "randWeighted", lambda skill: 0.5)
    p = make_paradigm(XkorOrdinalParadigm,
                       opts={"statuses": ["DNF"], "statusProbs": [1.0], "statusSortOrder": [10.0]},
                       sport=sport)

    p.scorinate([make_athlete(name="A")])

    r = p.res[0]
    assert r.scoreString() == "DNF"
    assert r.score() == pytest.approx(0.5 - 10.0)


def test_scorinate_short_circuits_when_a_required_value_is_missing():
    sport = make_sport(seed=1)
    p = make_paradigm(XkorOrdinalParadigm, opts={}, sport=sport)
    p.requiredValues = ["someStat"]

    p.scorinate([make_athlete(name="A")])

    assert p.out == [("", "Sport does not support this paradigm")]
    assert p.res == []
