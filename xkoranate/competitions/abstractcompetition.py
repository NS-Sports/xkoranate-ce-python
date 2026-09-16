import math

from xkoranate.athlete import XkorAthlete, isBye
from xkoranate.result import XkorResult
from xkoranate.sport import XkorSport
from xkoranate.startlist import XkorStartList, XkorStartListGroup
from xkoranate.tablegenerator.decider import nudgeForShootout
from xkoranate.variant import toDouble, toList, toString


class XkorAbstractCompetition:
    def __init__(self, sl=None, s=None, paradigmOptions=None, competitionOptions=None, results=None):
        self.resultsBuf = {}  # QHash<int, QString>
        self.resumeOpt = {}
        self.userOpt = {}
        self.startList = XkorStartList()
        self.sport = XkorSport()
        self.paradigmOpt = {}
        if sl is not None:
            self.init(sl, s, paradigmOptions, competitionOptions, results)

    def acceptsByes(self):
        """Whether this competition understands bye entrants.

        Only a knockout bracket does. Everything else gets them stripped out
        in init(), so a group used for a cup can be reused for a league
        without phantom participants turning up in the results.
        """
        return False

    def hasOptionsWidget(self):
        return False

    def init(self, sl, s, paradigmOptions, competitionOptions, results):
        # C++ copies the start list by value; copy the group structure so that
        # later changes to the caller's start list don't leak into us
        self.startList = XkorStartList()
        self.startList.name = sl.name
        keep = (lambda a: True) if self.acceptsByes() else (lambda a: not isBye(a))
        self.startList.groups = [XkorStartListGroup(g.name, [a for a in g.athletes if keep(a)])
                                 for g in sl.groups]
        self.sport = s
        self.paradigmOpt = dict(paradigmOptions)
        self.userOpt = dict(competitionOptions)
        self.resultsBuf = dict(results)

    def matchdays(self):
        raise NotImplementedError  # pure virtual

    def matchdayNames(self):
        raise NotImplementedError  # pure virtual

    def nameWidth(self):
        maximumWidth = 20
        showTeamNames = 1 if toString(self.paradigmOpt.get("showTLAs", "true")) == "true" else 0
        groups = self.startList.groups
        for i in groups:
            for j in i.athletes:
                if len(j.name) + showTeamNames * (3 + len(j.nation)) > maximumWidth:
                    maximumWidth = len(j.name) + showTeamNames * (3 + len(j.nation))
        return maximumWidth

    def newOptionsWidget(self, options):
        return None

    def schedule(self):
        """Full fixture list across every matchday, before any results are
        generated. Returns None for competition types that don't have a
        fixed matchday-vs-matchday schedule (e.g. individually-scored
        events)."""
        return None

    def matchOdds(self, matchday, trials=1000):
        """Per-fixture win/draw/loss percentages for the given matchday,
        estimated from skills alone (no results required). Returns None
        for competition types or paradigms that don't support a head-to-head
        odds estimate (e.g. individually-scored events)."""
        return None

    def supportsOdds(self):
        return False

    def _oddsParadigm(self):
        """The event's paradigm, if it can estimate head-to-head odds."""
        from xkoranate.paradigms.abstracth2hparadigm import XkorAbstractH2HParadigm
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        p = XkorParadigmFactory.newParadigmForSport(self.sport, dict(self.paradigmOpt))
        return p if isinstance(p, XkorAbstractH2HParadigm) else None

    def effectiveScores(self, paradigm, score1, score2):
        """Two scores with any tiebreaker rolled in, and an "OT"/"SO" tag.

        A match settled in extra time carries the extra goals in the score
        it is recorded with; one settled on penalties keeps its full-time
        score, because shootout goals don't belong in a table, but is still
        tagged as decided that way.
        """
        value1 = score1.score()
        value2 = score2.score()
        tiebreakers = toList(paradigm.option("tiebreakers"))
        tiebreakerNames = toList(paradigm.option("tiebreakerNames"))

        decider = None
        shootoutName = None
        used = []  # extraTime and goldenGoal can share the "OT" name
        for i in range(len(tiebreakerNames)):
            name = toString(tiebreakerNames[i])
            kind = toString(tiebreakers[i]) if i < len(tiebreakers) else ""
            if not (score1.contains(name) or score2.contains(name)):
                continue
            if kind == "shootout":
                decider = "SO"
                shootoutName = name
            elif name not in used:
                value1 += toDouble(score1.value(name))
                value2 += toDouble(score2.value(name))
                used.append(name)
                decider = "OT"

        if decider == "SO" and shootoutName is not None:
            # the shootout may not have followed a stage that separated them
            # (extra time can stay scoreless), so nudge the winner ahead
            value1, value2 = nudgeForShootout(
                value1, value2,
                toDouble(score1.value(shootoutName)),
                toDouble(score2.value(shootoutName)))

        return (value1, value2, decider)

    def _formatAthleteName(self, athlete):
        showTLAs = toString(self.paradigmOpt.get("showTLAs", "true")) == "true"
        if showTLAs and athlete.nation:
            return "%s (%s)" % (athlete.name, athlete.nation)
        return athlete.name

    def _formatFixture(self, home, away):
        return "%s v %s" % (self._formatAthleteName(home), self._formatAthleteName(away))

    def _formatOdds(self, paradigm, home, away, trials):
        odds = paradigm.estimateOdds(home, away, trials)
        return "%s v %s — %s %.0f%%  Draw %.0f%%  %s %.0f%%" % (
            self._formatAthleteName(home), self._formatAthleteName(away),
            self._formatAthleteName(home), odds["win"] * 100,
            odds["draw"] * 100,
            self._formatAthleteName(away), odds["loss"] * 100)

    def rankedListOutput(self, title, results, comparator):
        rankDigits = (int(math.log10(len(results))) + 1) if len(results) > 0 else 1
        rval = " " * (rankDigits + 1) + title + "\n"
        prev = XkorResult()
        for i in range(len(results)):
            # if prev.athlete is set && (prev == results[i] || (!isRankable(prev) && !isRankable(results[i])))
            if (not (prev.athlete == XkorAthlete())) \
                    and ((not comparator(prev, results[i]) and not comparator(results[i], prev))
                         or (not comparator.isRankable(prev) and not comparator.isRankable(results[i]))):
                rval += " " * (rankDigits + 1) + results[i].output() + "\n"
            elif not comparator.isRankable(results[i]) and comparator.isRankable(prev):
                rval += "—".rjust(rankDigits) + " " + results[i].output() + "\n"
            else:
                rval += str(i + 1).rjust(rankDigits) + " " + results[i].output() + "\n"
            prev = results[i]
        rval += "\n"
        return rval

    def results(self, matchday):
        return self.resultsBuf.get(matchday, "")

    def resumeFileOptions(self):
        return dict(self.resumeOpt)

    def revertToMatchday(self, matchday):
        # given matchday is the first that will be erased
        return {}

    def scorinate(self, matchday):
        raise NotImplementedError  # pure virtual
