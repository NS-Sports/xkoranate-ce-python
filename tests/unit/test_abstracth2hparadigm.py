import pytest
from builders import make_athlete, make_paradigm, make_sport, stub_uniform

from xkoranate.paradigms.abstracth2hparadigm import XkorAbstractH2HParadigm
from xkoranate.paradigms.lisaparadigm import XkorLISAParadigm
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


def test_a_gaelic_result_shows_the_extra_time_score(monkeypatch):
    p = make_paradigm(_MinimalH2HParadigm,
                       opts={"resultStyle": "gaelic", "tiebreakerNames": ["AET"],
                             "pointValues": [3, 1], "attackCoeffs": [1, 1], "etAttackCoeff": 1.0},
                       sport=make_sport(seed=1))
    home = XkorResult(15, ath=make_athlete(name="Home", nation="AAA"))
    away = XkorResult(15, ath=make_athlete(name="Away", nation="BBB"))
    home.result["subScores"] = [1, 12]
    away.result["subScores"] = [0, 15]
    # extra time: home 1 goal 1 point, away 0 goals 2 points
    goals = iter([1, 0, 1, 2])
    monkeypatch.setattr(p, "generateScore", lambda *args: next(goals))
    home, away = p.generateETScore(home, away, "AET")

    line = p.formatGaelicScore(home, away)

    # was "( (0) –  (0))": the total and the breakdown were swapped
    assert line == "Home (AAA) 1-12 (15) drew with Away (BBB) 0-15 (15) (1-1 (4) – 0-2 (2))"


def test_generateSOScore_stops_once_the_margin_cannot_be_overcome(monkeypatch):
    sport = make_sport(seed=1)
    stub_uniform(monkeypatch, sport, [0.0, 1.0])  # home scores, away misses
    p = make_paradigm(_MinimalH2HParadigm, opts={"shootoutLength": 1, "shootoutProb": 0.5}, sport=sport)
    home_res = XkorResult(ath=make_athlete(name="Home"))
    away_res = XkorResult(ath=make_athlete(name="Away"))

    home, away = p.generateSOScore(home_res, away_res, "kicks")

    assert home.value("kicks") == 1
    assert away.value("kicks") is None  # away's kick never went in, so it's never written


@pytest.mark.parametrize("opts", [{"shootoutLength": 5},
                                  {"shootoutLength": 5, "shootoutProb": 0},
                                  {"shootoutLength": 5, "shootoutProb": 1}])
def test_generateSOScore_skips_a_shootout_no_kick_can_separate(monkeypatch, opts):
    sport = make_sport(seed=1)
    stub_uniform(monkeypatch, sport, [])  # any kick at all would raise
    p = make_paradigm(_MinimalH2HParadigm, opts=opts, sport=sport)

    home, away = p.generateSOScore(XkorResult(ath=make_athlete(name="Home")),
                                   XkorResult(ath=make_athlete(name="Away")), "kicks")

    assert not p.shootoutCanDecide()
    assert home.value("kicks") is None and away.value("kicks") is None


def test_lisa_shootouts_decide_without_a_shootoutProb():
    # LISA's Qusma kicks carry their own probabilities
    p = make_paradigm(XkorLISAParadigm, opts={}, sport=make_sport(seed=1))
    assert p.shootoutCanDecide()


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


# --- extra periods the sport cuts short ---------------------------------------

class _FixedDrawH2HParadigm(XkorAbstractH2HParadigm):
    """Hands out a fixed count of each kind of score, home then away."""

    def __init__(self, sport, user_opts, counts):
        super().__init__(sport, user_opts)
        self._counts = iter(counts)

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        return next(self._counts)


RUGBY_LEAGUE = {"pointValues": [4, 2, 1], "attackCoeffs": [1, 1, 1], "etAttackCoeff": 1.0,
                "conversionValues": [2], "conversionSelection": [1.0], "conversionSuccess": [1.0],
                "suddenDeathExtraTime": 1}


def extra_period(opts, counts):
    p = _FixedDrawH2HParadigm(make_sport(seed=1), {}, counts)
    p.opt = opts
    home = XkorResult(ath=make_athlete(name="Home"))
    away = XkorResult(ath=make_athlete(name="Away"))
    return p.generateETScore(home, away, "AET")


def test_golden_point_keeps_one_score_of_the_best_kind_without_its_conversion():
    # drawn: home 2 tries and a drop goal, away a penalty goal (home, away
    # per kind); home went ahead first and a try ends it before the kick
    home, away = extra_period(RUGBY_LEAGUE, [2, 0, 0, 1, 1, 0])
    assert (home.value("AET"), away.value("AET")) == (4, 0)
    assert (home.value("AETSubScores"), away.value("AETSubScores")) == ([1, 0, 0], [0, 0, 0])


def test_golden_point_level_on_points_means_nobody_scored():
    home, away = extra_period(RUGBY_LEAGUE, [0, 0, 1, 1, 0, 0])
    assert (home.value("AET"), away.value("AET")) == (0, 0)


def test_one_side_scores_keeps_everything_the_winner_drew():
    opts = dict(RUGBY_LEAGUE, suddenDeathExtraTime=0, extraTimeOneSideScores=1,
                conversionSuccess=[0.0])
    # drawn: away a try and a drop goal (5), home a drop goal (1)
    home, away = extra_period(opts, [0, 1, 0, 0, 1, 1])
    assert (home.value("AET"), away.value("AET")) == (0, 5)


def test_a_full_extra_period_is_left_alone():
    opts = dict(RUGBY_LEAGUE, suddenDeathExtraTime=0, conversionSuccess=[0.0])
    home, away = extra_period(opts, [1, 1, 0, 0, 0, 1])
    assert (home.value("AET"), away.value("AET")) == (4, 5)


# --- LISA shootouts ------------------------------------------------------------

def lisa_shootout(monkeypatch, kicks):
    """kicks: True/False for each kick in the order they're drawn, home
    then away; every kick after those misses."""
    sport = make_sport(seed=1)
    it = iter(kicks)
    monkeypatch.setattr(sport, "randUniform", lambda: 0.0 if next(it, False) else 0.99)
    p = make_paradigm(XkorLISAParadigm, opts={}, sport=sport)
    home, away = p.generateSOScore(XkorResult(ath=make_athlete(name="Home")),
                                   XkorResult(ath=make_athlete(name="Away")), "pen.")
    return home.value("pen.") or 0, away.value("pen.") or 0


def test_a_lisa_shootout_stops_when_the_side_behind_cant_catch_up(monkeypatch):
    # 3 out of 3 against 0 out of 3: two kicks left can't make up three
    assert lisa_shootout(monkeypatch, [True, False] * 3) == (3, 0)


def test_a_lisa_shootout_can_end_before_the_away_side_kicks(monkeypatch):
    # 3–1 after three each; the home side's fourth makes it 4–1 with the
    # away side two kicks from 3, so its fourth kick never counts
    assert lisa_shootout(monkeypatch, [True, False, True, False, True, True, True, True]) == (4, 1)


def test_a_lisa_shootout_goes_to_sudden_death_after_five_each(monkeypatch):
    # all ten in, then the home side misses and the away side scores
    assert lisa_shootout(monkeypatch, [True] * 10 + [False, True]) == (5, 6)


def test_lisa_shootouts_only_end_the_ways_a_football_shootout_can():
    for seed in range(300):
        p = make_paradigm(XkorLISAParadigm, opts={}, sport=make_sport(seed=seed))
        home, away = p.generateSOScore(XkorResult(ath=make_athlete(name="Home")),
                                       XkorResult(ath=make_athlete(name="Away")), "pen.")
        h, a = home.value("pen.") or 0, away.value("pen.") or 0
        assert h != a
        if max(h, a) > 5:
            assert abs(h - a) == 1  # past five each, only sudden death
        else:
            assert abs(h - a) <= 3  # a gap of 4 or more is settled sooner
