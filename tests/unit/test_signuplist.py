import uuid

import pytest

from xkoranate.athlete import XkorAthlete
from xkoranate.exceptions import XkorSearchFailedException
from xkoranate.signuplist import XkorSignupList


def test_addAthlete_generates_id_when_missing():
    sl = XkorSignupList()
    a = XkorAthlete()
    sl.addAthlete(a)
    assert a.id is not None
    assert sl.athletes() == [a]


def test_addAthlete_preserves_existing_id():
    sl = XkorSignupList()
    fixed_id = uuid.uuid4()
    a = XkorAthlete(fixed_id)
    sl.addAthlete(a)
    assert a.id == fixed_id


def test_setAthletes_generates_ids_only_when_missing():
    sl = XkorSignupList()
    fixed_id = uuid.uuid4()
    a1 = XkorAthlete(fixed_id)
    a2 = XkorAthlete()
    sl.setAthletes([a1, a2])
    assert a1.id == fixed_id
    assert a2.id is not None
    assert sl.athletes() == [a1, a2]


def test_getAthleteByID_found_and_missing():
    sl = XkorSignupList()
    a = XkorAthlete()
    sl.addAthlete(a)
    assert sl.getAthleteByID(a.id) is a
    with pytest.raises(XkorSearchFailedException):
        sl.getAthleteByID(uuid.uuid4())


def test_default_rank_bounds():
    sl = XkorSignupList()
    assert sl.minRank() == 0.0
    assert sl.maxRank() == 1.0


def test_adjustRank_scales_between_min_and_max():
    sl = XkorSignupList()
    sl.setMinRank(0.0)
    sl.setMaxRank(2.0)
    assert sl.adjustRank(1.0) == 0.5
    assert sl.adjustRank(0.0) == 0.0
    assert sl.adjustRank(2.0) == 1.0


def test_generateID_produces_unique_uuids():
    sl = XkorSignupList()
    ids = {sl.generateID() for _ in range(50)}
    assert len(ids) == 50


def test_adjustRank_survives_a_degenerate_range():
    """max == min divided by zero, which crashed scorination outright.

    A freshly added participant sitting at the minimum, or a field where
    everyone carries the same rating, gets there without anything unusual.
    """
    sl = XkorSignupList()
    sl.setMinRank(1.0)
    sl.setMaxRank(1.0)
    # mid-range: an unrankable field is evenly matched rather than uniformly
    # weakest, which is what 0.0 would generate for a score-based sport
    assert sl.adjustRank(1.0) == 0.5
    assert sl.adjustRank(5.0) == 0.5
