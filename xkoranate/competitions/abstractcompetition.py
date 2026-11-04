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

    def supportsQualifications(self):
        """Whether formatQualifications() can mark qualified (Q) and
        eliminated (E) entrants in this competition's standings."""
        return False

    def formatQualifications(self, text, matchday, settings):
        """The results text for `matchday` with Q/E markers added under the
        given QualificationSettings. Display-only: the stored results stay
        plain, so changing the rule never needs a re-roll. Returns `text`
        unchanged when there's nothing it can mark."""
        return text

    def _newParadigm(self, **extra):
        """The sport's paradigm for scorinating, with the `extra` options and
        the name column width on top of the event's own."""
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions.update(extra)
        localParadigmOptions["nameWidth"] = self.nameWidth()
        return XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

    def allowsDraws(self):
        return toString(self.userOpt.get("allowDraws")) != "false"

    def _breakDrawnPairs(self, p, count=None):
        """Settle every drawn match among p's results, which pair up two by
        two in order; only the first `count` results (default: all) count."""
        results = list(p.results())
        if count is None:
            count = len(results)
        for j in range(0, count - (count % 2), 2):
            if p.compare(results[j], results[j + 1]) == 0:
                p.breakTie([results[j].athlete, results[j + 1].athlete])

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

    def tableScores(self, paradigm, score1, score2, allowDraws=True):
        """The scores a league table records for a match, and an "OT"/"SO" tag.

        A stoppage (KO, DSQ, RSC, …) has no real score: the paradigm marks
        the beaten side with a status and parks the largest float on each
        side, the wrong way round for a table, which counts the higher score
        as the win. Adding those up also overflows to infinity. So a
        stoppage goes in as 1–0 to the winner, the way a shootout winner is
        credited one goal (see nudgeForShootout).

        With draws allowed a tie is a result in its own right, so the
        tiebreaker stages don't come into the table.
        """
        if toString(score1.value("status")) != "":
            return (0.0, 1.0, None)
        if toString(score2.value("status")) != "":
            return (1.0, 0.0, None)
        if allowDraws:
            return (score1.score(), score2.score(), None)
        return self.effectiveScores(paradigm, score1, score2)

    def _formatAthleteName(self, athlete):
        showTLAs = toString(self.paradigmOpt.get("showTLAs", "true")) == "true"
        if showTLAs and athlete.nation:
            return "%s (%s)" % (athlete.name, athlete.nation)
        return athlete.name

    def _formatFixture(self, home, away):
        return "%s v %s" % (self._formatAthleteName(home), self._formatAthleteName(away))

    @staticmethod
    def _fixtureLines(sections, line, headings=True):
        """line(home, away) for every fixture in `sections`, a list of
        (heading, fixtures) pairs, each section under its heading if
        `headings`. Sections with no fixtures are left out."""
        lines = []
        for heading, fixtures in sections:
            if not fixtures:
                continue
            if headings:
                lines.append(heading)
            for home, away in fixtures:
                lines.append(line(home, away))
        return lines

    @staticmethod
    def _oddsText(lines):
        return "\n".join(lines) + ("\n" if lines else "")

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

    def _clearResultsFrom(self, matchday):
        """Blank the results of `matchday` and every one after it."""
        for k in list(self.resultsBuf.keys()):
            if k >= matchday:
                self.resultsBuf[k] = ""

    def resumeFileOptions(self):
        return dict(self.resumeOpt)

    def revertToMatchday(self, matchday):
        # given matchday is the first that will be erased
        return {}

    def scorinate(self, matchday):
        raise NotImplementedError  # pure virtual
