"""Unit checks for the LISA v1.093 paradigm's math helpers.

Expected values are taken from the worked examples in the original design
write-up, cross-checked against formulas read directly out of a reference
spreadsheet's cells rather than relying on the write-up's prose alone.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from xkoranate.paradigms.lisaparadigm import XkorLISAParadigm


def make_paradigm(**opts):
    p = XkorLISAParadigm()
    p.opt = opts
    p.userOpt = {}
    return p


def approx(a, b, tol=1e-3):
    return abs(a - b) < tol


# --- EAR / win probability formulas (unchanged from v1.0 to v1.093) ---

p = make_paradigm(powerScalar=1.984, refRank=10.93, REAR=300)
ear_at_ref_rank = p._ear(10.93)
assert approx(ear_at_ref_rank, 300, tol=1e-6), ear_at_ref_rank  # REAR is EAR at the reference rank, by construction

drawP, homeWinP, awayWinP = p._winDrawProbabilities(500, 500)
# equal teams: u = xW = 0.5, so DrawP = u-u^2 = 0.25 and each side splits the
# remaining 0.75 evenly (both are simultaneously "the underdog" at u=xW)
assert approx(drawP, 0.25), drawP
assert approx(homeWinP, 0.375) and approx(awayWinP, 0.375), (homeWinP, awayWinP)
assert approx(drawP + homeWinP + awayWinP, 1.0), (drawP, homeWinP, awayWinP)

# --- winning margin distribution (mean and P(margin=1), using the OLD
#     divisor of 500 for these specific worked examples, which predate the
#     v1.093 "margin divisor" concept) ---

p500 = make_paradigm(marginDivisor=500)


def zt_poisson_mean(lam):
    return lam / (1 - math.exp(-lam))


def zt_poisson_p1(lam):
    return lam / (math.exp(lam) - 1)


lam0 = p500._marginLambda(0)
assert approx(lam0, 1.093), lam0
assert approx(zt_poisson_mean(lam0), 1.644, tol=0.01), zt_poisson_mean(lam0)
assert approx(zt_poisson_p1(lam0), 0.551, tol=0.001), zt_poisson_p1(lam0)

lam350 = p500._marginLambda(350)  # favourite wins by a big EAR gap
assert approx(lam350, 2.201, tol=0.001), lam350
assert approx(zt_poisson_mean(lam350), 2.475, tol=0.01), zt_poisson_mean(lam350)
assert approx(zt_poisson_p1(lam350), 0.274, tol=0.001), zt_poisson_p1(lam350)

lamNeg350 = p500._marginLambda(-350)  # underdog wins by the same gap
# note: the forum post's prose actually mislabels P(margin=1) as "λ = 0.753"
# for this example; the real lambda (~0.543) is what reproduces its own
# stated mean (1.296) and P(margin=1) (75.3%) figures, checked below
assert approx(lamNeg350, 0.5427, tol=0.001), lamNeg350
assert approx(zt_poisson_mean(lamNeg350), 1.296, tol=0.01), zt_poisson_mean(lamNeg350)
assert approx(zt_poisson_p1(lamNeg350), 0.753, tol=0.001), zt_poisson_p1(lamNeg350)

# --- v1.093's revised losing-team-score lambda, checked against the mock
#     sheet's live cell CG5 (NetStyle=9.000, margin=2 -> lambda=0.690) ---

p750 = make_paradigm(marginDivisor=750)
assert approx(p750._losingScoreLambda(netStyle=9.0, margin=2), 0.690, tol=0.001)

# large margins should suppress the loser's expected goals more than small
# ones do, for the same style sum (the actual "Scorigami Mitigation" change)
lam_small_margin = p750._losingScoreLambda(netStyle=0, margin=1)
lam_large_margin = p750._losingScoreLambda(netStyle=0, margin=8)
assert lam_large_margin < lam_small_margin, (lam_small_margin, lam_large_margin)


# --- extra-time decisive-result probability (t) and favourite-win-given-
#     decisive probability (w), checked against the sheet's CL/CM columns
#     (CL5=MAX(0.4,...), not the forum prose's approximated gAbs>10 cutoff) ---

p_et = make_paradigm()
t_small_gap = p_et._etDecisiveProbability(5)
assert approx(t_small_gap, 0.4), t_small_gap  # floored below the ~9.99 crossover

t_big_gap = p_et._etDecisiveProbability(350)
assert approx(t_big_gap, 0.58987, tol=1e-4), t_big_gap
w_big_gap = p_et._etFavouriteWinProbability(t_big_gap)
assert approx(w_big_gap, 0.70265, tol=1e-4), w_big_gap

assert p_et._etFavouriteWinProbability(0.4) == 0.5  # floored t always splits 50/50

# --- per-event overrides: a user-set value in userOpt wins over the sport
#     file's default, and untouched constants still fall back to it ---

p_override = make_paradigm(powerScalar=1.984, refRank=10.93, REAR=300, marginDivisor=750)
p_override.userOpt = {"REAR": 450}
assert p_override.REAR() == 450
assert p_override.powerScalar() == 1.984
assert p_override.refRank() == 10.93
assert p_override.marginDivisor() == 750

# --- estimateOdds() is overridden to be exact/deterministic (no Monte
#     Carlo needed, unlike every other H2H paradigm), since regular-time
#     win/draw/loss is fully determined by the EAR gap ---

from xkoranate.athlete import XkorAthlete as _XkorAthleteForOdds  # noqa: E402

p_odds = make_paradigm(powerScalar=1.984, refRank=10.93, REAR=300, homeAdvantageEAR=100)
p_odds.userOpt = {"homeAdvantage": "true"}
homeAth = _XkorAthleteForOdds()
homeAth.rpSkill = 25.0
awayAth = _XkorAthleteForOdds()
awayAth.rpSkill = 2.0
# deliberately no p_odds.s (PRNG) set -- estimateOdds() should need none

odds = p_odds.estimateOdds(homeAth, awayAth)
assert approx(odds["win"], 0.9421, tol=1e-3), odds
assert approx(odds["win"] + odds["draw"] + odds["loss"], 1.0, tol=1e-9), odds
assert p_odds.estimateOdds(homeAth, awayAth) == odds  # deterministic, not sampled


# --- home advantage modes: "fixed" (default) uses the flat EAR magnitude
#     directly; "adversarial" and "individual" let each team set its own
#     rating as a participant column instead ---

from xkoranate.athlete import XkorAthlete  # noqa: E402


def make_athlete(homeAdvantage=None):
    a = XkorAthlete()
    if homeAdvantage is not None:
        a.setProperty("homeAdvantage", str(homeAdvantage))
    return a


p_mode = make_paradigm(homeAdvantageEAR=120)
assert p_mode.homeAdvantageMode() == "fixed"  # default, with no userOpt override at all

# --- adversarial: each side's own -5..+5 rating maps onto 0..homeAdvantageEAR()
#     (v=0 -> half the baseline, matching the style column's neutral-zero
#     convention), and the two sides' mapped ratings sum together ---

p_mode.userOpt = {"homeAdvantageMode": "adversarial"}
assert p_mode.homeAdvantageMode() == "adversarial"

fortress = make_athlete(5)  # "an absolute fortress" -- maps to the full baseline (120)
default_ = make_athlete(0)  # untouched -- maps to half the baseline (60)
assert p_mode._homeAdvantageValue(fortress, default_) == 180  # 120 + 60
assert p_mode._homeAdvantageValue(default_, fortress) == 180  # same either way round

unset = make_athlete()  # no rating entered at all -- same as an explicit 0
assert p_mode._homeAdvantageValue(fortress, unset) == 180

both_unset = p_mode._homeAdvantageValue(make_athlete(), make_athlete())
assert both_unset == 120, both_unset  # 60+60 -- reproduces the flat baseline exactly

low_h = make_athlete(-5)
high_h = make_athlete(5)
cancelled = p_mode._homeAdvantageValue(low_h, high_h)
assert cancelled == 120, cancelled  # 0 + 120 -- cancels out to the normal baseline

# --- individual: only the home team's own uncapped rating applies; the
#     away side's rating is irrelevant to this specific match ---

p_mode.userOpt = {"homeAdvantageMode": "individual"}
assert p_mode.homeAdvantageMode() == "individual"

homeRated = make_athlete(500)  # uncapped -- can exceed the baseline entirely
awayRated = make_athlete(500)  # irrelevant when away, since individual mode ignores it
assert p_mode._homeAdvantageValue(homeRated, awayRated) == 500
assert p_mode._homeAdvantageValue(homeRated, make_athlete()) == 500  # away's rating never matters

homeUnset = make_athlete()
assert p_mode._homeAdvantageValue(homeUnset, awayRated) == 120  # unset home defaults to the baseline

# --- fixed: falls back to the flat EAR magnitude regardless of any
#     per-team ratings that might be sitting unused on the athletes ---

p_mode.userOpt = {"homeAdvantageMode": "fixed"}
assert p_mode._homeAdvantageValue(fortress, default_) == 120

print("ALL LISA PARADIGM TESTS PASSED")
