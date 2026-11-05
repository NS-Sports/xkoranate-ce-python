"""Scorinate every sport file under every competition its paradigm supports,
and group whatever raises by where it raised.

    QT_QPA_PLATFORM=offscreen pixi run -e dev python tools/sweep.py [FILTER]

For each sport (or each whose name contains FILTER) and each supported
competition, plays 8 athletes in two groups and 6 in one, then the default
competition once more with home advantage on and TLAs off. Then plays a
two-leg round robin of 6 under every table sort criterion, for the two
association football formulas. Each run draws from its own Mt19937, so a
failure reproduces on its own.

Prints one block per distinct stack (exception, innermost frames), listing
the sport × competition × setup runs that hit it. Paradigm debug output goes
to stderr; redirect it away to read the report.
"""

import collections
import os
import signal
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from builders import CONF_NAMES, GROUP_NAMES, event_for, play  # noqa: E402
from xkoranate.application import XkorApplication  # noqa: E402
from xkoranate.competitions.competitionfactory import XkorCompetitionFactory  # noqa: E402
from xkoranate.competitions.qualification import QualificationSettings  # noqa: E402
from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory  # noqa: E402
from xkoranate.rng import Mt19937  # noqa: E402
from xkoranate.tablegenerator.tablesorter import SORT_RULES  # noqa: E402
from xkoranate.xml.xmlindex import XkorXmlIndex  # noqa: E402
from xkoranate.xml.xmlsportreader import XkorXmlSportReader  # noqa: E402

SEED = 2026
VARIANT_SEED = 7
CRITERIA_SEED = 99
CRITERIA_SPORTS = ("Association football—LISA formula", "Association football—SQIS formula")
SETUPS = (("8 in 2 groups", dict(n=8, groups=[4, 4])), ("6 in 1 group", dict(n=6)))
VARIANT = {"homeAdvantage": "true", "showTLAs": "false"}
QUALIFICATIONS = (QualificationSettings("top", 2), QualificationSettings("topPlusBest", 1, 1))
TIMEOUT = 20  # seconds per run; a knockout shootout can loop forever


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout("run took over %ds" % TIMEOUT)


def stack_key(exc):
    """The exception and its innermost three frames inside xkoranate."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__)
              if os.sep + "xkoranate" + os.sep in f.filename]
    where = tuple("%s:%d %s" % (os.path.relpath(f.filename, ROOT), f.lineno, f.name)
                  for f in frames[-3:])
    return type(exc).__name__, str(exc)[:80], where


def criteria_options(criteria):
    return {"sortCriteria": criteria, "numberOfLegs": "2", "pointsForWin": "2",
            "pointsForDraw": "1", "showResultsGrid": "true"}


def run(index, sportName, competition, n, groups=None, paradigm_options=None, seed=SEED,
        options=None):
    names = CONF_NAMES if competition == "interConference" else GROUP_NAMES
    ev, sport = event_for(index, Mt19937(seed), sportName, n=n, groups=groups, names=names,
                          competition=competition, options=options)
    if paradigm_options:
        ev.setParadigmOptions(dict(paradigm_options))
    c = play(ev, sport)
    if c.supportsQualifications():
        for md in range(c.matchdays()):
            for settings in QUALIFICATIONS:
                c.formatQualifications(c.results(md), md, settings)


def main(filter_text=None):
    app = XkorApplication.instance() or XkorApplication([])
    app.refreshSearchPaths()
    index = XkorXmlIndex()
    index.traverse("sports:")
    signal.signal(signal.SIGALRM, _alarm)

    jobs = []  # (sport, competition, label, run() keywords)
    for sportName, sportFile in index.getAllFiles().items():
        if filter_text and filter_text not in sportName:
            continue
        paradigm = XkorParadigmFactory.newParadigmForSport(XkorXmlSportReader(sportFile).sport(), {})
        jobs += [(sportName, competition, label, kw)
                 for competition in XkorCompetitionFactory.competitionTypes()
                 if paradigm.supportsCompetition(competition)
                 for label, kw in SETUPS]
        jobs.append((sportName, paradigm.defaultCompetition(),
                     "8 in 1 group, home advantage, no TLAs",
                     dict(n=8, paradigm_options=VARIANT, seed=VARIANT_SEED)))
    for sportName in CRITERIA_SPORTS:
        if filter_text and filter_text not in sportName:
            continue
        for criterion in SORT_RULES:
            for criteria in ([criterion], [criterion, "points", "goalDifference"]):
                jobs.append((sportName, "roundRobin", "6 in 1 group, sorted by %s" % criteria,
                             dict(n=6, seed=CRITERIA_SEED, options=criteria_options(criteria))))

    failures = collections.defaultdict(list)
    for sportName, competition, label, kw in jobs:
        signal.alarm(TIMEOUT)
        try:
            run(index, sportName, competition, **kw)
        except Exception as exc:  # noqa: BLE001 -- the point is to catch everything
            failures[stack_key(exc)].append("%s × %s (%s)" % (sportName, competition, label))
        finally:
            signal.alarm(0)

    total = sum(len(v) for v in failures.values())
    print("%d runs, %d failed, %d distinct stacks\n" % (len(jobs), total, len(failures)))
    for (name, message, where), hits in sorted(failures.items(), key=lambda kv: -len(kv[1])):
        print("%s: %s  [%d]" % (name, message, len(hits)))
        for frame in where:
            print("    at", frame)
        for hit in hits:
            print("    -", hit)
        print()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
