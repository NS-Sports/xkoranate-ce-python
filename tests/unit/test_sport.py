"""The random-number helpers, and the domain guards on their shape parameters."""

import math

import pytest

from xkoranate.rng import Mt19937
from xkoranate.sport import XkorSport


@pytest.fixture
def sport():
    s = XkorSport()
    s.setPRNG(Mt19937(2026))
    return s


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
