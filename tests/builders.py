"""Shared construction helpers for the test suite.

Plain functions, not fixtures -- import what you need, or just construct
inline if that reads more clearly for a given test. conftest.py wraps
tournament() in a fixture.
"""

import uuid

from xkoranate.athlete import XkorAthlete
from xkoranate.competitions.competitionfactory import XkorCompetitionFactory
from xkoranate.event import XkorEvent
from xkoranate.group import XkorGroup
from xkoranate.rng import Mt19937
from xkoranate.rplist import XkorRPList
from xkoranate.signuplist import XkorSignupList
from xkoranate.sport import XkorSport
from xkoranate.tablegenerator.table import XkorTable
from xkoranate.tablegenerator.tablematch import XkorTableMatch
from xkoranate.xml.xmlsportreader import XkorXmlSportReader

NATIONS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]
GROUP_NAMES = ["Group %s" % letter for letter in "ABCDEFGH"]
CONF_NAMES = ["Conf %d" % (i + 1) for i in range(8)]

LISA = "Association football—LISA formula"
SQIS = "Association football—SQIS formula"
SPRINT = "Athletics—Men’s 00100 m—Round 1"
PLAYOFF = {"thirdPlacePlayoff": "true"}


# --- paradigms -----------------------------------------------------------------

def make_sport(seed=None, paradigm_options=None, data_points=None):
    sport = XkorSport()
    sport.r = Mt19937(seed)
    sport.m_paradigmOptions = paradigm_options or {}
    sport.m_dataPoints = data_points or {}
    return sport


def make_athlete(name="A", nation="", skill=0.5, rp_skill=None, athlete_id=None, **properties):
    """One athlete; any other keyword becomes a property, e.g. style=3."""
    athlete = XkorAthlete(athlete_id)
    athlete.name = name
    athlete.nation = nation
    athlete.skill = skill
    athlete.rpSkill = skill if rp_skill is None else rp_skill
    for key, value in properties.items():
        athlete.setProperty(key, value)
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


# --- athletes and events -------------------------------------------------------

def _numbered(text, number):
    return text % number if "%" in text else text


def make_athletes(n=8, name="Athlete %d", nation=None, skills=None):
    """n athletes, or one for each name if n is a list of names.

    `name` and `nation` take the 1-based number if they hold a %, and
    nations cycle through NATIONS by default. Skills default to (i+1)/(n+1),
    so the last is the strongest.

    Ids are uuid4s: XkorSignupList seeds its own from the clock, so two lists
    made within the same second hand out the same ones.
    """
    names = [_numbered(name, i + 1) for i in range(n)] if isinstance(n, int) else list(n)
    return [make_athlete(athleteName,
                         NATIONS[i % len(NATIONS)] if nation is None else _numbered(nation, i + 1),
                         (i + 1) / float(len(names) + 1) if skills is None else skills[i],
                         athlete_id=uuid.uuid4())
            for i, athleteName in enumerate(names)]


def make_signup_list(athletes, min_rank=0.0, max_rank=1.0):
    sl = XkorSignupList()
    sl.setMinRank(min_rank)
    sl.setMaxRank(max_rank)
    for athlete in athletes:
        sl.addAthlete(athlete)
    return sl


def make_event(athletes, groups=None, names=GROUP_NAMES, name="", sport=None, paradigm="",
               competition="", options=None):
    """An event for these athletes.

    `groups` is None for one group of everyone, a list of sizes to split
    them into in signup order, or a list of id lists; `names` names them.
    """
    ev = XkorEvent()
    ev.setName(name)
    ev.setSignupList(make_signup_list(athletes))
    if sport is not None:
        ev.setSport(sport, paradigm)
    ev.setCompetition(competition)
    ev.setCompetitionOptions(dict(options or {}))
    ids = [a.id for a in athletes]
    if groups is None:
        groups = [ids]
    elif all(isinstance(size, int) for size in groups):
        ends = [sum(groups[:i + 1]) for i in range(len(groups))]
        groups = [ids[end - size:end] for size, end in zip(groups, ends)]
    for groupName, members in zip(names, groups):
        ev.addGroup(XkorGroup(groupName, list(members)))
    return ev


def event_for(index, rng, sport_name, n=None, **kw):
    """(event, sport) for a sport file, with the sport drawing from `rng`.

    n athletes from make_athletes(), defaulting to the sum of the group
    sizes or 8; anything else goes to make_event(). Building draws nothing
    from `rng`.
    """
    sport = XkorXmlSportReader(index.lookup(sport_name)).sport()
    sport.setPRNG(rng)
    if n is None:
        groups = kw.get("groups")
        n = sum(groups) if groups and isinstance(groups[0], int) else 8
    ev = make_event(make_athletes(n), name="Test " + sport_name, sport=sport_name,
                    paradigm=sport.paradigm(), **kw)
    return ev, sport


def new_competition(ev, sport, start_list=None, competition=None):
    """The event's competition, built from its saved options and results."""
    return XkorCompetitionFactory.newCompetitionFull(
        competition or ev.competition(),
        ev.makeStartList(XkorRPList()) if start_list is None else start_list,
        sport, ev.paradigmOptions(), ev.competitionOptions(), ev.results())


def play(ev, sport, start_list=None, up_to=None):
    """Play matchdays the way the GUI does: a fresh competition for each,
    built from what the last one saved into the event. Returns the one built
    after the last matchday played."""
    sl = ev.makeStartList(XkorRPList()) if start_list is None else start_list
    c = new_competition(ev, sport, sl)
    for md in range(c.matchdays() if up_to is None else up_to):
        c.scorinate(md)
        ev.replaceCompetitionOptions(c.resumeFileOptions())
        ev.setResult(md, c.results(md))
        c = new_competition(ev, sport, sl)
    return c


# --- named tournaments ---------------------------------------------------------
# The few events most integration tests play, as event_for() arguments that
# a test can override. One per case:
#   cup of 12            LISA knockout, 16-slot bracket, four first-round byes
#   cup of 12, playoff   the same with a third-place playoff before the final
#   cup of 8             a full bracket: quarter-finals, semi-finals, final
#   cup of 8, playoff    the same with a playoff, for the schedule's numbering
#   cup of 4             semi-finals and a final, for picking single matches
#   league 3×4           SQIS round robin, "Group A" to "Group C"
#   heats 3×5            three 100 m heats of five, mass start
#   conferences 4+4      LISA inter-conference play, "Conf 1" and "Conf 2"

CUP = dict(sport_name=LISA, competition="singleElimination")

TOURNAMENTS = {
    "cup of 12": dict(CUP, n=12),
    "cup of 12, playoff": dict(CUP, n=12, options=PLAYOFF),
    "cup of 8": dict(CUP, n=8),
    "cup of 8, playoff": dict(CUP, n=8, options=PLAYOFF),
    "cup of 4": dict(CUP, n=4),
    "league 3×4": dict(sport_name=SQIS, competition="roundRobin", groups=[4, 4, 4]),
    "heats 3×5": dict(sport_name=SPRINT, competition="standard", groups=[5, 5, 5]),
    "conferences 4+4": dict(sport_name=LISA, competition="interConference", groups=[4, 4],
                            names=CONF_NAMES),
}


def tournament(name, index, rng, **overrides):
    """(event, sport) for one of TOURNAMENTS, with any argument overridden."""
    kw = dict(TOURNAMENTS[name], **overrides)
    return event_for(index, rng, kw.pop("sport_name"), **kw)


# --- tables --------------------------------------------------------------------

OT_POINTS = {"ot_win": "setPointsForOTWin", "so_win": "setPointsForSOWin",
             "ot_loss": "setPointsForOTLoss", "so_loss": "setPointsForSOLoss"}


def make_table(win=3, draw=1, loss=0, criteria=None, matches=(), **ot):
    """A table with these points and sort criteria, and matches given as
    (team1, team2, score1, score2[, decider]). ot_win, so_win, ot_loss and
    so_loss override the overtime points, which otherwise follow win/loss."""
    t = XkorTable()
    t.setPointsForWin(win)
    t.setPointsForDraw(draw)
    t.setPointsForLoss(loss)
    for key, value in ot.items():
        getattr(t, OT_POINTS[key])(value)
    if criteria is not None:
        t.setSortCriteria(criteria)
    t.setMatches([XkorTableMatch(*m) for m in matches])
    return t


def names(t):
    """A generated table's teams, top first."""
    return [row.name() for tier in t.data for row in tier]


def points(t):
    """A generated table's {team: points}."""
    return {row.name(): t.getPoints(row) for tier in t.data for row in tier}
