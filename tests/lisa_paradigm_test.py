"""Unit checks for the LISA v1.093 paradigm's math helpers.

Expected values are taken from the worked examples in the original design
write-up, cross-checked against formulas read directly out of a reference
spreadsheet's cells rather than relying on the write-up's prose alone.
"""

import math

from builders import make_athlete, make_paradigm

from xkoranate.paradigms.lisaparadigm import XkorLISAParadigm


def lisa(**opts):
    return make_paradigm(XkorLISAParadigm, opts)


def approx(a, b, tol=1e-3):
    return abs(a - b) < tol


def rated(homeAdvantage=None):
    """An athlete with a home-advantage rating, or none entered at all."""
    if homeAdvantage is None:
        return make_athlete()
    return make_athlete(homeAdvantage=str(homeAdvantage))


# --- EAR / win probability formulas (unchanged from v1.0 to v1.093) ---

def test_rear_is_the_ear_at_the_reference_rank():
    p = lisa(powerScalar=1.984, refRank=10.93, REAR=300)
    ear_at_ref_rank = p._ear(10.93)
    assert approx(ear_at_ref_rank, 300, tol=1e-6), ear_at_ref_rank  # by construction


def test_equal_teams_split_the_win_probability_evenly():
    p = lisa(powerScalar=1.984, refRank=10.93, REAR=300)
    drawP, homeWinP, awayWinP = p._winDrawProbabilities(500, 500)
    # equal teams: u = xW = 0.5, so DrawP = u-u^2 = 0.25 and each side splits the
    # remaining 0.75 evenly (both are simultaneously "the underdog" at u=xW)
    assert approx(drawP, 0.25), drawP
    assert approx(homeWinP, 0.375) and approx(awayWinP, 0.375), (homeWinP, awayWinP)
    assert approx(drawP + homeWinP + awayWinP, 1.0), (drawP, homeWinP, awayWinP)


# --- winning margin distribution (mean and P(margin=1), using the OLD
#     divisor of 500 for these specific worked examples, which predate the
#     v1.093 "margin divisor" concept) ---

def zt_poisson_mean(lam):
    return lam / (1 - math.exp(-lam))


def zt_poisson_p1(lam):
    return lam / (math.exp(lam) - 1)


def test_margin_for_an_even_match():
    lam0 = lisa(marginDivisor=500)._marginLambda(0)
    assert approx(lam0, 1.093), lam0
    assert approx(zt_poisson_mean(lam0), 1.644, tol=0.01), zt_poisson_mean(lam0)
    assert approx(zt_poisson_p1(lam0), 0.551, tol=0.001), zt_poisson_p1(lam0)


def test_margin_when_the_favourite_wins():
    lam350 = lisa(marginDivisor=500)._marginLambda(350)  # by a big EAR gap
    assert approx(lam350, 2.201, tol=0.001), lam350
    assert approx(zt_poisson_mean(lam350), 2.475, tol=0.01), zt_poisson_mean(lam350)
    assert approx(zt_poisson_p1(lam350), 0.274, tol=0.001), zt_poisson_p1(lam350)


def test_margin_when_the_underdog_wins():
    lamNeg350 = lisa(marginDivisor=500)._marginLambda(-350)  # by the same gap
    # note: the forum post's prose actually mislabels P(margin=1) as "λ = 0.753"
    # for this example; the real lambda (~0.543) is what reproduces its own
    # stated mean (1.296) and P(margin=1) (75.3%) figures, checked below
    assert approx(lamNeg350, 0.5427, tol=0.001), lamNeg350
    assert approx(zt_poisson_mean(lamNeg350), 1.296, tol=0.01), zt_poisson_mean(lamNeg350)
    assert approx(zt_poisson_p1(lamNeg350), 0.753, tol=0.001), zt_poisson_p1(lamNeg350)


# --- v1.093's revised losing-team-score lambda, checked against the mock
#     sheet's live cell CG5 (NetStyle=9.000, margin=2 -> lambda=0.690) ---

def test_losing_score_lambda_matches_the_sheet():
    p750 = lisa(marginDivisor=750)
    assert approx(p750._losingScoreLambda(netStyle=9.0, margin=2), 0.690, tol=0.001)


def test_large_margins_suppress_the_losers_goals():
    # more than small ones do, for the same style sum (the actual
    # "Scorigami Mitigation" change)
    p750 = lisa(marginDivisor=750)
    lam_small_margin = p750._losingScoreLambda(netStyle=0, margin=1)
    lam_large_margin = p750._losingScoreLambda(netStyle=0, margin=8)
    assert lam_large_margin < lam_small_margin, (lam_small_margin, lam_large_margin)


# --- extra-time decisive-result probability (t) and favourite-win-given-
#     decisive probability (w), checked against the sheet's CL/CM columns
#     (CL5=MAX(0.4,...), not the forum prose's approximated gAbs>10 cutoff) ---

def test_extra_time_probabilities_match_the_sheet():
    p_et = lisa()
    t_small_gap = p_et._etDecisiveProbability(5)
    assert approx(t_small_gap, 0.4), t_small_gap  # floored below the ~9.99 crossover

    t_big_gap = p_et._etDecisiveProbability(350)
    assert approx(t_big_gap, 0.58987, tol=1e-4), t_big_gap
    w_big_gap = p_et._etFavouriteWinProbability(t_big_gap)
    assert approx(w_big_gap, 0.70265, tol=1e-4), w_big_gap

    assert p_et._etFavouriteWinProbability(0.4) == 0.5  # floored t always splits 50/50


# --- per-event overrides: a user-set value in userOpt wins over the sport
#     file's default, and untouched constants still fall back to it ---

def test_a_user_set_value_overrides_the_sport_file():
    p_override = lisa(powerScalar=1.984, refRank=10.93, REAR=300, marginDivisor=750)
    p_override.userOpt = {"REAR": 450}
    assert p_override.REAR() == 450
    assert p_override.powerScalar() == 1.984
    assert p_override.refRank() == 10.93
    assert p_override.marginDivisor() == 750


# --- estimateOdds() is overridden to be exact/deterministic (no Monte
#     Carlo needed, unlike every other H2H paradigm), since regular-time
#     win/draw/loss is fully determined by the EAR gap ---

def test_estimated_odds_are_exact():
    p_odds = lisa(powerScalar=1.984, refRank=10.93, REAR=300, homeAdvantageEAR=100)
    p_odds.userOpt = {"homeAdvantage": "true"}
    homeAth = make_athlete(rp_skill=25.0)
    awayAth = make_athlete(rp_skill=2.0)
    # deliberately no p_odds.s (PRNG) set -- estimateOdds() should need none

    odds = p_odds.estimateOdds(homeAth, awayAth)
    assert approx(odds["win"], 0.9421, tol=1e-3), odds
    assert approx(odds["win"] + odds["draw"] + odds["loss"], 1.0, tol=1e-9), odds
    assert p_odds.estimateOdds(homeAth, awayAth) == odds  # deterministic, not sampled


# --- home advantage modes: "fixed" (default) uses the flat EAR magnitude
#     directly; "adversarial" and "individual" let each team set its own
#     rating as a participant column instead ---

def test_home_advantage_is_fixed_by_default():
    p_mode = lisa(homeAdvantageEAR=120)
    assert p_mode.homeAdvantageMode() == "fixed"  # with no userOpt override at all


def test_adversarial_home_advantage_sums_both_ratings():
    # each side's own -5..+5 rating maps onto 0..homeAdvantageEAR() (v=0 ->
    # half the baseline, matching the style column's neutral-zero
    # convention), and the two sides' mapped ratings sum together
    p_mode = lisa(homeAdvantageEAR=120)
    p_mode.userOpt = {"homeAdvantageMode": "adversarial"}
    assert p_mode.homeAdvantageMode() == "adversarial"

    fortress = rated(5)  # "an absolute fortress" -- maps to the full baseline (120)
    default_ = rated(0)  # untouched -- maps to half the baseline (60)
    assert p_mode._homeAdvantageValue(fortress, default_) == 180  # 120 + 60
    assert p_mode._homeAdvantageValue(default_, fortress) == 180  # same either way round

    unset = rated()  # no rating entered at all -- same as an explicit 0
    assert p_mode._homeAdvantageValue(fortress, unset) == 180

    both_unset = p_mode._homeAdvantageValue(rated(), rated())
    assert both_unset == 120, both_unset  # 60+60 -- reproduces the flat baseline exactly

    cancelled = p_mode._homeAdvantageValue(rated(-5), rated(5))
    assert cancelled == 120, cancelled  # 0 + 120 -- cancels out to the normal baseline


def test_individual_home_advantage_uses_only_the_home_rating():
    # only the home team's own uncapped rating applies; the away side's
    # rating is irrelevant to this specific match
    p_mode = lisa(homeAdvantageEAR=120)
    p_mode.userOpt = {"homeAdvantageMode": "individual"}
    assert p_mode.homeAdvantageMode() == "individual"

    homeRated = rated(500)  # uncapped -- can exceed the baseline entirely
    awayRated = rated(500)  # irrelevant when away, since individual mode ignores it
    assert p_mode._homeAdvantageValue(homeRated, awayRated) == 500
    assert p_mode._homeAdvantageValue(homeRated, rated()) == 500  # away's rating never matters

    homeUnset = rated()
    assert p_mode._homeAdvantageValue(homeUnset, awayRated) == 120  # unset home defaults to the baseline


def test_fixed_home_advantage_ignores_the_ratings():
    # falls back to the flat EAR magnitude regardless of any per-team
    # ratings that might be sitting unused on the athletes
    p_mode = lisa(homeAdvantageEAR=120)
    p_mode.userOpt = {"homeAdvantageMode": "fixed"}
    assert p_mode._homeAdvantageValue(rated(5), rated(0)) == 120
