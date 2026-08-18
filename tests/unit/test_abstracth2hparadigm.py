from paradigm_helpers import make_athlete, make_paradigm, make_sport, stub_uniform

from xkoranate.paradigms.abstracth2hparadigm import XkorAbstractH2HParadigm
from xkoranate.result import XkorResult


class _MinimalH2HParadigm(XkorAbstractH2HParadigm):
    """Concrete stand-in so the shared machinery in XkorAbstractH2HParadigm
    can be exercised without pulling in a specific sport's scoring math."""

    def generateScore(self, skill, oppSkill, style, oppStyle,
                       homeAdvantage=False, attackMultiplier=1):
        return skill - oppSkill


def test_generateStatus_returns_status_whose_cumulative_prob_is_reached():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm, opts={"statuses": ["injury"], "statusProbs": [1.0]}, sport=sport)
    assert p.generateStatus() == "injury"


def test_generateStatus_returns_empty_when_none_configured():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm, opts={}, sport=sport)
    assert p.generateStatus() == ""


def test_generateDecisionScore_favors_the_higher_skilled_athlete():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm, sport=sport)

    home_wins = 0
    trials = 200
    for _ in range(trials):
        home = XkorResult(ath=make_athlete(name="Home", rp_skill=0.9))
        away = XkorResult(ath=make_athlete(name="Away", rp_skill=0.1))
        home, away = p.generateDecisionScore(home, away, "")
        if "decision" in home.result:
            home_wins += 1

    assert home_wins > trials * 0.8


def test_generateETScore_accumulates_across_point_value_entries():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm,
                       opts={"pointValues": [1, 2], "attackCoeffs": [1, 1], "etAttackCoeff": 1.0},
                       sport=sport)
    home_res = XkorResult(ath=make_athlete(name="Home", rp_skill=0.8))
    away_res = XkorResult(ath=make_athlete(name="Away", rp_skill=0.3))

    home, away = p.generateETScore(home_res, away_res, "")

    # our stub generateScore(skill, opp) = skill - opp = 0.5 each call
    assert home.value("score") == 0.5 * 3
    assert away.value("score") == -0.5 * 3
    assert home.value("subScores") == [0.5, 0.5]


def test_generateSOScore_stops_once_the_margin_cannot_be_overcome(monkeypatch):
    sport = make_sport(seed=1)
    stub_uniform(monkeypatch, sport, [0.0, 1.0])  # home scores, away misses
    p = make_paradigm(_MinimalH2HParadigm, opts={"shootoutLength": 1, "shootoutProb": 0.5}, sport=sport)
    home_res = XkorResult(ath=make_athlete(name="Home"))
    away_res = XkorResult(ath=make_athlete(name="Away"))

    home, away = p.generateSOScore(home_res, away_res, "kicks")

    assert home.value("kicks") == 1
    assert away.value("kicks") is None  # away's kick never went in, so it's never written


def test_generateStyleModification_default_mode_preserves_margin_sign(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "individualScore", lambda index, skill: 3)
    p = make_paradigm(_MinimalH2HParadigm, opts={}, sport=sport)

    home, away = p.generateStyleModification(5, 2, 1.0, -1.0)

    assert (home, away) == (8, 5)


def test_generateStyleModification_default_mode_clamps_effect_to_preserve_outcome(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "individualScore", lambda index, skill: -10)
    p = make_paradigm(_MinimalH2HParadigm, opts={}, sport=sport)

    home, away = p.generateStyleModification(5, 2, 1.0, -1.0)

    assert home > away  # home was winning before the style effect; still is
    assert (home, away) == (1, 0)


def test_generateStyleModification_nsfs_mode_breaks_ties_to_preserve_winner(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randGaussian", lambda: 0.0)
    # coeffB=0 zeroes out the exponential term entirely, making the
    # multiplier exactly coeffA + offset regardless of style/gaussian inputs
    opts = {
        "NSFSStyleCoeffA": 0.15,
        "NSFSStyleCoeffB": 0.0,
        "NSFSStyleExponent": 0.0,
        "NSFSStyleOffset": 0.0,
    }
    p = make_paradigm(_MinimalH2HParadigm, opts=opts, user_opts={"NSFSStyleMods": "true"}, sport=sport)

    # 10 * 0.15 = 1.5 -> int 1; 9 * 0.15 = 1.35 -> int 1 -- a tie that must
    # be broken back in favour of the original winner (home, 10 > 9)
    home, away = p.generateStyleModification(10, 9, 0.0, 0.0)

    assert home == 2
    assert away == 1


def test_generateConversions_always_succeeds_when_probabilities_are_one():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm,
                       opts={"conversionValues": [1], "conversionSelection": [1.0], "conversionSuccess": [1.0]},
                       sport=sport)
    assert p.generateConversions(3) == 3


def test_generateConversions_never_succeeds_when_probability_is_zero():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm,
                       opts={"conversionValues": [1], "conversionSelection": [1.0], "conversionSuccess": [0.0]},
                       sport=sport)
    assert p.generateConversions(3) == 0


def test_generateGGScore_awards_configured_point_value_to_the_scorer(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randUniform", lambda: 0.0)
    monkeypatch.setattr(sport, "randWeightedH2H", lambda skill, opp: 1.0 if skill > opp else 0.0)
    p = make_paradigm(_MinimalH2HParadigm,
                       opts={"goldenGoalProb": 1.0, "pointValues": [6], "goldenGoalPointProbs": [1.0],
                             "homeAdvantageGG": 0.0},
                       sport=sport)
    home_res = XkorResult(ath=make_athlete(name="Home", rp_skill=0.9))
    away_res = XkorResult(ath=make_athlete(name="Away", rp_skill=0.1))

    home, away = p.generateGGScore(home_res, away_res, "")

    assert home.value("score") == 6
    assert away.value("score") is None


def test_generateIFAFScore_only_the_team_that_clears_the_threshold_scores(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randUniform", lambda: 0.9)  # > 0.5 -> home team goes first
    monkeypatch.setattr(sport, "randWeightedH2H", lambda skill, opp: 0.5 if skill == 0.9 else 2.0)
    p = make_paradigm(_MinimalH2HParadigm,
                       opts={"ifafPointProbs": [1.0], "pointValues": [6], "homeAdvantageIFAF": 0.0,
                             # generateConversions indexes conversionSelection[0] unconditionally
                             # whenever count >= 1, even if conversionValues is empty
                             "conversionValues": [1], "conversionSelection": [1.0], "conversionSuccess": [0.0]},
                       sport=sport)
    home_res = XkorResult(ath=make_athlete(name="Home", rp_skill=0.9))
    away_res = XkorResult(ath=make_athlete(name="Away", rp_skill=0.1))

    home, away = p.generateIFAFScore(home_res, away_res, "score", otNumber=1)

    assert home.value("score") == 6
    assert away.value("score") == 0


def test_scorinate_pairs_athletes_into_home_away_matches():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm, opts={"pointValues": [1], "attackCoeffs": [1]}, sport=sport)
    athletes = [make_athlete(name=n, rp_skill=0.5) for n in ("A", "B", "C", "D")]

    p.scorinate(athletes)

    assert len(p.res) == 4
    assert [name for name, _ in p.out] == ["A", "C"]


def test_scorinate_short_circuits_when_a_required_value_is_missing():
    sport = make_sport(seed=1)
    p = make_paradigm(_MinimalH2HParadigm, opts={}, sport=sport)
    p.requiredValues = ["someStat"]

    p.scorinate([make_athlete(name="A"), make_athlete(name="B")])

    assert p.out == [("", "Sport does not support this paradigm")]
    assert p.res == []


def test_estimateOdds_does_not_perturb_the_shared_rng_sequence():
    home = make_athlete(name="Home", rp_skill=0.6)
    away = make_athlete(name="Away", rp_skill=0.4)
    opts = {"pointValues": [1], "attackCoeffs": [1]}

    sport_a = make_sport(seed=7, paradigm_options=opts)
    _MinimalH2HParadigm(sport_a, {})
    sequence_without_estimate = [sport_a.r.next32() for _ in range(5)]

    sport_b = make_sport(seed=7, paradigm_options=opts)
    paradigm_b = _MinimalH2HParadigm(sport_b, {})
    paradigm_b.estimateOdds(home, away, trials=50)
    sequence_after_estimate = [sport_b.r.next32() for _ in range(5)]

    assert sequence_without_estimate == sequence_after_estimate
