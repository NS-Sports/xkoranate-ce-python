"""Shared construction helpers for paradigm unit tests.

Plain functions, not fixtures -- import what you need, or just construct
inline if that reads more clearly for a given test.
"""

from xkoranate.athlete import XkorAthlete
from xkoranate.rng import Mt19937
from xkoranate.sport import XkorSport


def make_sport(seed=None, paradigm_options=None, data_points=None):
    sport = XkorSport()
    sport.r = Mt19937(seed)
    sport.m_paradigmOptions = paradigm_options or {}
    sport.m_dataPoints = data_points or {}
    return sport


def make_athlete(name="A", nation="", skill=0.5, rp_skill=None, style=None, athlete_id=None):
    athlete = XkorAthlete(athlete_id)
    athlete.name = name
    athlete.nation = nation
    athlete.skill = skill
    athlete.rpSkill = skill if rp_skill is None else rp_skill
    if style is not None:
        athlete.setProperty("style", style)
    return athlete


def make_paradigm(cls, opts=None, user_opts=None, sport=None):
    """Build a paradigm instance.

    Without `sport`, constructs bare and hand-sets .opt/.userOpt -- the fast
    path for pure-math tests that never touch self.s. With `sport`, goes
    through the real init() contract (sport.paradigmOptions() populates
    .opt unless `opts` is given to override it).
    """
    if sport is not None:
        paradigm = cls(sport, user_opts or {})
        if opts is not None:
            paradigm.opt = opts
    else:
        paradigm = cls()
        paradigm.opt = opts or {}
        paradigm.userOpt = user_opts or {}
    return paradigm


def stub_uniform(monkeypatch, sport, values):
    """Replace sport.randUniform with a fixed sequence of return values, to
    force specific probability branches deterministically instead of
    reverse-engineering which seed produces which Mt19937 output."""
    it = iter(values)
    monkeypatch.setattr(sport, "randUniform", lambda: next(it))
