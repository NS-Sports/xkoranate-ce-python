"""The random-number helpers, and the domain guards on their shape parameters."""

import math

import pytest
from builders import make_sport


@pytest.fixture
def sport():
    return make_sport(2026)


@pytest.mark.parametrize("skill", [-50.0, -1.0, 0.0, 0.5, 1.0, 27.0, 92.0, 1e6])
def test_randWeightedFull_holds_up_for_a_skill_outside_the_normal_range(sport, skill):
    """A skill outside [0, 1] made a shape parameter non-positive, which is a
    negative exponent on a zero base: "math domain error", taking down the
    whole scorination.

    Switching an event from a paradigm that passes skill through to one that
    rescales left the signup list's ceiling at 1.0, so skills entered on a
    0-100 scale normalised to 27-92 rather than 0.27-0.92.
    """
    for _ in range(50):
        rval = sport.randWeightedFull(skill, 1.02, 2.4, 3.8, False)
        assert 0.0 <= rval <= 1.0
        assert not math.isnan(rval)


@pytest.mark.parametrize("skill", [-3.0, 0.0, 0.4, 1.0, 45.0])
def test_randWeighted_and_h2h_hold_up_too(sport, skill):
    """The two entry points every paradigm actually calls."""
    for _ in range(20):
        assert 0.0 <= sport.randWeighted(skill) <= 1.0
        assert 0.0 <= sport.randWeightedH2H(skill, 1.0 - skill) <= 1.0


@pytest.mark.parametrize("a,b", [(0.0, 1.0), (1.0, 0.0), (0.0, 0.0), (-1.0, -1.0)])
def test_rand_kumaraswamy_clamps_a_non_positive_shape_parameter(sport, a, b):
    for skew in (True, False):
        rval = sport.rand_kumaraswamy(a, b, skew)
        assert 0.0 <= rval <= 1.0


def test_randGaussian_survives_the_rngs_minimum_value(sport):
    """randUniform() returns exactly 0.0 at the Twister's minimum, and log(0)
    is the same domain error rand_kumaraswamy() was hardened against."""
    sport.randUniform = lambda: 0.0
    rval = sport.randGaussian()
    assert not math.isnan(rval)
    assert not math.isinf(rval)


def test_randGaussianCapped_stays_inside_its_cap(sport):
    sport.randUniform = lambda: 0.0
    assert 0.1 <= sport.randGaussianCapped(0.1) <= 0.9


# --- the ends of a data-point scale ----------------------------------------------

def scale_sport(**options):
    return make_sport(1, paradigm_options=options, data_points={"score": {0.1: 10.0, 0.9: 90.0}})


def test_transformNumber_carries_the_line_on_past_the_data_points_by_default():
    assert scale_sport().transformNumber(0.0, "score") == pytest.approx(0.0)
    assert scale_sport().transformNumber(1.0, "score") == pytest.approx(100.0)


def test_transformNumber_holds_a_scale_to_the_ends_the_sport_file_names():
    sport = scale_sport(scoreMin=5.0, scoreMax=95.0)
    assert sport.transformNumber(0.0, "score") == 5.0
    assert sport.transformNumber(1.0, "score") == 95.0
    assert sport.transformNumber(0.5, "score") == pytest.approx(50.0)
