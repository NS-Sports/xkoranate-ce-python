import math

from xkoranate.athlete import isBye
from xkoranate.competitions import bracket
from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.tablegenerator.decider import nudgeForShootout
from xkoranate.variant import qNumber, toDouble, toInt, toList, toString

BYE_MARKER = "— BYE —"
BYE_ADVANCES = "BYE — advances"
COIN_TOSS = "coin toss"
THIRD_PLACE_ROUND = "3P"  # sentinel round marker for the third-place playoff
_FIELD_SEP = "|"


def _roundName(matchesInRound):
    """Name a round by how many matches it contains."""
    if matchesInRound == 1:
        return "Final"
    if matchesInRound == 2:
        return "Semi-finals"
    if matchesInRound == 4:
        return "Quarter-finals"
    return "Round of %d" % (matchesInRound * 2)


class XkorSingleEliminationCompetition(XkorAbstractCompetition):
    """A knockout bracket: losers are out, winners meet in the next round.

    The first-round draw is made once, when the first round is scorinated,
    and persisted — it is random for most seeding methods, so it cannot be
    regenerated. Every later round's fixtures are derived from the winners
    of the round before it.
    """

    def __init__(self, *args, **kwargs):
        # set before super(), which may call init()
        self._draw = None  # list of XkorAthlete|None, one per bracket slot
        self._rows = None  # list of result row strings
        self._byId = None  # athlete id -> athlete, built on first use
        super().__init__(*args, **kwargs)

    def init(self, sl, s, paradigmOptions, competitionOptions, results):
        super().init(sl, s, paradigmOptions, competitionOptions, results)
        self._draw = None
        self._rows = None
        self._byId = None

    def acceptsByes(self):
        return True  # a bye holds a slot in the draw, so keep them

    def hasOptionsWidget(self):
        return True

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.singleeliminationcompetitionoptions import (
            XkorSingleEliminationCompetitionOptions,
        )

        return XkorSingleEliminationCompetitionOptions(competitionOptions)

    # ---------------------------------------------------------------- entrants

    def _entrants(self):
        """Every athlete in the start list, all groups pooled, in order."""
        rval = []
        for g in self.startList.groups:
            rval.extend(g.athletes)
        return rval

    def _realEntrants(self):
        """Entrants excluding the byes that hold empty slots in the draw."""
        return [a for a in self._entrants() if not isBye(a)]

    def _bracketSize(self):
        if len(self._realEntrants()) < 2:
            return 0
        return bracket.bracketSize(len(self._realEntrants()))

    def _rounds(self):
        size = self._bracketSize()
        if size == 0:
            return 0
        return int(math.log2(size))

    def _thirdPlaceEnabled(self):
        return (toString(self.userOpt.get("thirdPlacePlayoff", "false")) == "true"
                and self._rounds() >= 2)

    # ------------------------------------------------------------- matchdays

    def matchdays(self):
        rounds = self._rounds()
        if rounds == 0:
            return 0
        return rounds + (1 if self._thirdPlaceEnabled() else 0)

    def matchdayNames(self):
        rounds = self._rounds()
        if rounds == 0:
            return []
        names = [_roundName(1 << (rounds - 1 - r)) for r in range(rounds)]
        if self._thirdPlaceEnabled():
            names.insert(rounds - 1, "Third-place playoff")  # played before the final
        return names

    def _roundForMatchday(self, matchday):
        """(bracket round, is the third-place playoff) for a matchday index."""
        rounds = self._rounds()
        if not self._thirdPlaceEnabled():
            return (matchday, False)
        if matchday == rounds - 1:
            return (rounds - 2, True)  # contested by the losers of the semi-finals
        if matchday >= rounds:
            return (rounds - 1, False)  # the final, pushed back one matchday
        return (matchday, False)

    def _matchdayForRound(self, round_):
        """Inverse of _roundForMatchday for real bracket rounds."""
        rounds = self._rounds()
        if self._thirdPlaceEnabled() and round_ == rounds - 1:
            return rounds
        return round_

    # ----------------------------------------------------------------- state

    def _loadState(self):
        """Read the draw and played matches, preferring what we hold in memory.

        The GUI rebuilds this object after every matchday, which promotes
        resumeOpt into userOpt; a headless caller reuses one object and
        never does. Keeping both paths working means checking memory first
        and falling back to the options we were constructed with.
        """
        if self._rows is None:
            self._rows = [toString(i) for i in toList(self.userOpt.get("bracketResults")) if toString(i) != ""]
        if self._draw is None:
            raw = [toString(i) for i in toList(self.userOpt.get("bracketDraw"))]
            if raw and self._orderMatchesDraw(raw):
                self._draw = [self._athleteById(i) for i in raw]
            elif raw:
                # the user has rearranged the bracket since this draw was
                # made, so it — and the results that came out of it — no
                # longer describe this tournament
                self._rows = []

    def _orderMatchesDraw(self, raw):
        """Whether a stored draw still matches the bracket as it stands now.

        Compared against the draw the current entrant order would produce,
        not the order itself: a bare list of entrants and the full slot list
        it expands to describe the same bracket.
        """
        derived = ["" if a is None else str(a.id)
                   for a in bracket.drawFromOrder(self._entrants())]
        return derived == list(raw)

    def _saveState(self):
        self.resumeOpt["bracketDraw"] = ([(str(a.id) if a is not None else "") for a in self._draw]
                                         if self._draw is not None else [])
        self.resumeOpt["bracketResults"] = list(self._rows)

    def _makeDraw(self):
        # the draw is whatever order the bracket editor left the entrants in,
        # byes included — the seeding buttons on that page do the arranging
        self._draw = bracket.drawFromOrder(self._entrants())

    # ------------------------------------------------------------- match rows

    def _makeRow(self, round_, match, home, away, score1, score2, decider, winner):
        return _FIELD_SEP.join([
            str(round_), str(match),
            str(home.id) if home is not None else "",
            str(away.id) if away is not None else "",
            qNumber(score1) if score1 is not None else "",
            qNumber(score2) if score2 is not None else "",
            decider or "",
            str(winner.id) if winner is not None else "",
        ])

    def _parseRow(self, row):
        f = row.split(_FIELD_SEP)
        if len(f) < 8:
            return None
        return {
            "round": f[0], "match": toInt(f[1]),
            "home": f[2], "away": f[3],
            "score1": toDouble(f[4]) if f[4] else None,
            "score2": toDouble(f[5]) if f[5] else None,
            "decider": f[6], "winner": f[7],
        }

    def _dropRowsForRound(self, round_):
        """Forget a round's results, so scorinating it again replaces them."""
        self._loadState()
        kept = []
        for row in self._rows:
            r = self._parseRow(row)
            if r is not None and r["round"] == str(round_):
                continue
            kept.append(row)
        self._rows = kept

    def _rowsForRound(self, round_):
        self._loadState()
        rval = {}
        for row in self._rows:
            r = self._parseRow(row)
            if r is not None and r["round"] == str(round_):
                rval[r["match"]] = r
        return rval

    def _athleteById(self, id):
        if not id:
            return None
        if self._byId is None:
            self._byId = {str(a.id): a for a in self._realEntrants()}
        return self._byId.get(id)

    def _winnersOfRound(self, round_):
        """Winners of every match in a round, or None if it isn't complete."""
        expected = 1 << (self._rounds() - 1 - round_)
        rows = self._rowsForRound(round_)
        if len(rows) < expected:
            return None
        rval = []
        for m in range(expected):
            if m not in rows:
                return None
            rval.append(self._athleteById(rows[m]["winner"]))
        return rval

    def _losersOfRound(self, round_):
        rows = self._rowsForRound(round_)
        rval = []
        for m in sorted(rows):
            row = rows[m]
            loser = row["away"] if row["winner"] == row["home"] else row["home"]
            athlete = self._athleteById(loser)
            if athlete is not None:
                rval.append(athlete)
        return rval

    def _fixtures(self, round_):
        """(home, away) pairs for a round, or None if not yet determined."""
        self._loadState()
        if round_ < 0 or round_ >= self._rounds():
            return None
        if round_ == 0:
            if self._draw is None:
                # no draw stored yet, but the entrant order already describes
                # one, so the pairings can be shown before anything is played
                return self._pairs(bracket.drawFromOrder(self._entrants()))
            slots = self._draw
        else:
            slots = self._winnersOfRound(round_ - 1)
            if slots is None:
                return None
        return self._pairs(slots)

    def _pairs(self, slots):
        return [(slots[2 * m], slots[2 * m + 1]) for m in range(len(slots) // 2)]

    # ---------------------------------------------------------------- output

    def _bracketHeader(self):
        entrants = len(self._realEntrants())
        size = self._bracketSize()
        byes = size - entrants
        rval = "%d entrants — %d-slot bracket" % (entrants, size)
        if byes > 0:
            rval += ", %d %s" % (byes, "bye" if byes == 1 else "byes")
        return rval

    def _byeLine(self, athlete):
        name = self._formatAthleteName(athlete)
        return "%s  %s" % (name.ljust(self.nameWidth()), BYE_ADVANCES)

    def _matchNumber(self, round_, match):
        """Matches numbered continuously across the bracket, first round first.

        Every match gets a number of its own so that later rounds can refer
        back to the ones that feed them.
        """
        base = 0
        for r in range(round_):
            base += 1 << (self._rounds() - 1 - r)
        number = base + match + 1
        if self._thirdPlaceEnabled() and round_ == self._rounds() - 1:
            # the playoff is played before the final and takes its number
            number += 1
        return number

    def _thirdPlaceMatchNumber(self):
        base = 0
        for r in range(self._rounds() - 1):
            base += 1 << (self._rounds() - 1 - r)
        return base + 1

    def _matchesInRound(self, round_):
        return 1 << (self._rounds() - 1 - round_)

    def _sourceLabel(self, round_, slot, outcome="winner"):
        """Who fills a slot in a round that hasn't been reached yet."""
        return "Match %d %s" % (self._matchNumber(round_ - 1, slot), outcome)

    def _slotLine(self, number, home, away, width):
        return "%s  %s v %s" % (("%d." % number).rjust(width),
                                home.ljust(self.nameWidth()), away)

    def schedule(self):
        if self._rounds() == 0:
            return None
        self._loadState()

        lines = [self._bracketHeader(), "Rounds: " + ", ".join(self.matchdayNames()), ""]
        if self._fixtures(0) is None:
            lines.append("No bracket has been set up yet.")
            return "\n".join(lines)

        names = self.matchdayNames()
        width = len("%d." % self._matchNumber(self._rounds() - 1, 0))

        for round_ in range(self._rounds()):
            fixtures = self._fixtures(round_)
            lines.append(names[self._matchdayForRound(round_)])
            for m in range(self._matchesInRound(round_)):
                if fixtures is not None:
                    home, away = fixtures[m]
                    homeLabel = self._formatAthleteName(home) if home is not None else BYE_MARKER
                    awayLabel = self._formatAthleteName(away) if away is not None else BYE_MARKER
                else:
                    # this round hasn't been reached, so name the matches that
                    # will decide who plays in it
                    homeLabel = self._sourceLabel(round_, 2 * m)
                    awayLabel = self._sourceLabel(round_, 2 * m + 1)
                lines.append(self._slotLine(self._matchNumber(round_, m), homeLabel, awayLabel, width))
            lines.append("")

            if self._thirdPlaceEnabled() and round_ == self._rounds() - 2:
                lines.append(names[self._rounds() - 1])  # the playoff, played before the final
                losers = self._losersOfRound(round_)
                if len(losers) == 2:
                    homeLabel = self._formatAthleteName(losers[0])
                    awayLabel = self._formatAthleteName(losers[1])
                else:
                    homeLabel = self._sourceLabel(round_ + 1, 0, "loser")
                    awayLabel = self._sourceLabel(round_ + 1, 1, "loser")
                lines.append(self._slotLine(self._thirdPlaceMatchNumber(),
                                            homeLabel, awayLabel, width))
                lines.append("")

        return "\n".join(lines).rstrip("\n") + "\n"

    # ------------------------------------------------------------------ odds

    def _oddsParadigm(self):
        from xkoranate.paradigms.abstracth2hparadigm import XkorAbstractH2HParadigm
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        p = XkorParadigmFactory.newParadigmForSport(self.sport, dict(self.paradigmOpt))
        return p if isinstance(p, XkorAbstractH2HParadigm) else None

    def supportsOdds(self):
        return self._rounds() > 0 and self._oddsParadigm() is not None

    def matchOdds(self, matchday, trials=1000):
        p = self._oddsParadigm()
        if p is None or self._rounds() == 0:
            return None
        self._loadState()

        round_, isThirdPlace = self._roundForMatchday(matchday)
        if isThirdPlace:
            losers = self._losersOfRound(round_)
            if len(losers) < 2:
                return None
            return self._formatOdds(p, losers[0], losers[1], trials) + "\n"

        fixtures = self._fixtures(round_)
        if fixtures is None:
            return None

        lines = []
        for home, away in fixtures:
            if home is None or away is None:
                present = home if home is not None else away
                if present is not None:
                    lines.append(self._byeLine(present))
            else:
                lines.append(self._formatOdds(p, home, away, trials))
        return "\n".join(lines) + ("\n" if lines else "")

    # ------------------------------------------------------------- scorinate

    def _newParadigm(self):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()
        return XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

    def _decideMatch(self, p, home, away):
        """Resolve one match to (score1, score2, decider, winner).

        A knockout cannot end level, so the tiebreak path runs regardless of
        the allowDraws option, and a coin flip is the last resort for a
        paradigm that still cannot separate the two.
        """
        score1 = p.findResult(home.id)
        score2 = p.findResult(away.id)

        if p.compare(score1, score2) == 0:
            p.breakTie([home, away])
            score1 = p.findResult(home.id)
            score2 = p.findResult(away.id)

        value1, value2, decider = self._effectiveScores(p, score1, score2)

        # a stoppage result names the loser directly (see
        # XkorAbstractH2HParadigm.outputLine): a status on one side means
        # that side was beaten
        if toString(score1.value("status")) != "":
            winner = away
        elif toString(score2.value("status")) != "":
            winner = home
        elif value1 > value2:
            winner = home
        elif value2 > value1:
            winner = away
        else:
            # nothing the paradigm offers separates them; flip for it
            winner = home if self._coinFlip() else away
            decider = COIN_TOSS

        return (value1, value2, decider, winner)

    def _effectiveScores(self, p, score1, score2):
        """Scores with any tiebreaker rolled in, plus an OT/SO tag.

        Mirrors the accumulation XkorRoundRobinCompetition does before
        inserting a match into a table, so a knockout tie decided in extra
        time or on penalties reads the same way here as it does there.
        """
        value1 = score1.score()
        value2 = score2.score()
        tiebreakers = toList(p.option("tiebreakers"))
        tiebreakerNames = toList(p.option("tiebreakerNames"))

        decider = None
        shootoutName = None
        usedNames = []  # extraTime and goldenGoal can share the "OT" name
        for i in range(len(tiebreakerNames)):
            name = toString(tiebreakerNames[i])
            kind = toString(tiebreakers[i]) if i < len(tiebreakers) else ""
            if not (score1.contains(name) or score2.contains(name)):
                continue
            if kind == "shootout":
                # shootout scores aren't part of the score line, but they do
                # decide the match
                decider = "SO"
                shootoutName = name
            elif name not in usedNames:
                value1 += toDouble(score1.value(name))
                value2 += toDouble(score2.value(name))
                usedNames.append(name)
                decider = "OT"

        if decider == "SO" and shootoutName is not None:
            value1, value2 = nudgeForShootout(
                value1, value2,
                toDouble(score1.value(shootoutName)),
                toDouble(score2.value(shootoutName)))

        return (value1, value2, decider)

    def _coinFlip(self):
        rng = self.sport.r
        if rng is None:
            from xkoranate.rng import Mt19937

            rng = Mt19937()
        return (rng.next32() & 1) == 0

    def scorinate(self, matchday):
        if self._rounds() == 0:
            return  # nothing to play

        self._loadState()

        round_, isThirdPlace = self._roundForMatchday(matchday)

        if round_ == 0 and not isThirdPlace and self._draw is None:
            self._makeDraw()

        if isThirdPlace:
            self._scorinateThirdPlace(matchday, round_)
        else:
            self._scorinateRound(matchday, round_)

        self._saveState()

    def _scorinateRound(self, matchday, round_):
        fixtures = self._fixtures(round_)
        if fixtures is None:
            # the previous round hasn't been played, so we don't know who is here
            return

        self._dropRowsForRound(round_)

        p = self._newParadigm()

        byes = []
        played = []  # (match index, home, away)
        for m, (home, away) in enumerate(fixtures):
            if home is None and away is None:
                continue  # can't happen: byeSlots keeps one entrant per match
            if home is None or away is None:
                byes.append((m, home if home is not None else away))
            else:
                played.append((m, home, away))

        athletes = []
        for _, home, away in played:
            athletes.append(home)
            athletes.append(away)
        if athletes:
            p.scorinate(athletes)

        advancing = []
        for m, athlete in byes:
            advancing.append(athlete)
            self._rows.append(self._makeRow(round_, m, athlete, None, None, None, "bye", athlete))

        tossed = []
        for m, home, away in played:
            score1, score2, decider, winner = self._decideMatch(p, home, away)
            advancing.append(winner)
            if decider == COIN_TOSS:
                tossed.append(winner)
            self._rows.append(self._makeRow(round_, m, home, away, score1, score2, decider, winner))

        self.resultsBuf[matchday] = self._formatRound(matchday, round_, p, byes, played, tossed)

    def _scorinateThirdPlace(self, matchday, semiFinalRound):
        losers = self._losersOfRound(semiFinalRound)
        if len(losers) < 2:
            self.resultsBuf[matchday] = (
                self.matchdayNames()[matchday] + "\n"
                + "Not enough semi-finalists to contest a third-place playoff.\n\n")
            return

        home, away = losers[0], losers[1]
        self._dropRowsForRound(THIRD_PLACE_ROUND)
        p = self._newParadigm()
        p.scorinate([home, away])
        score1, score2, decider, winner = self._decideMatch(p, home, away)
        self._rows.append(self._makeRow(THIRD_PLACE_ROUND, 0, home, away, score1, score2, decider, winner))

        lines = [self.matchdayNames()[matchday], "", p.output().rstrip("\n"), "",
                 "Third place", self._formatAthleteName(winner), ""]
        self.resultsBuf[matchday] = "\n".join(lines) + "\n"

    def _formatRound(self, matchday, round_, p, byes, played, tossed=()):
        lines = [self.matchdayNames()[matchday]]
        if matchday == 0:
            # the bracket size and bye count only need saying once
            lines.append(self._bracketHeader())
        lines.append("")

        if byes:
            lines.append("Byes")
            for _, athlete in byes:
                lines.append(self._byeLine(athlete))
            lines.append("")

        if played:
            output = p.output().rstrip("\n")
            if output:
                lines.append(output)
                lines.append("")

        if tossed:
            # some paradigms can't separate a tie at all (a single game of
            # chess, say), and a knockout still has to send someone through
            lines.append("Decided by coin toss")
            for athlete in tossed:
                lines.append(self._formatAthleteName(athlete))
            lines.append("")

        lines.extend(self._nextRoundLines(round_))
        return "\n".join(lines) + "\n"

    def _nextRoundLines(self, round_):
        """The fixtures this round has just set up, or the champion.

        Once a round is scored its winners are known, so the next round's
        pairings can be named outright rather than just listing who is
        through.
        """
        winners = self._winnersOfRound(round_)
        if winners is None:
            return []

        if round_ == self._rounds() - 1:
            if len(winners) == 1 and winners[0] is not None:
                return ["Champion", self._formatAthleteName(winners[0]), ""]
            return []

        nextRound = round_ + 1
        lines = ["Into the " + self.matchdayNames()[self._matchdayForRound(nextRound)]]
        for m in range(self._matchesInRound(nextRound)):
            home, away = winners[2 * m], winners[2 * m + 1]
            lines.append("%s  %s v %s" % (
                ("%d." % self._matchNumber(nextRound, m)).rjust(4),
                (self._formatAthleteName(home) if home is not None else BYE_MARKER).ljust(self.nameWidth()),
                self._formatAthleteName(away) if away is not None else BYE_MARKER))
        lines.append("")
        return lines

    # ---------------------------------------------------------------- revert

    def revertToMatchday(self, matchday):
        # "matchday" is the first that will be erased
        self._loadState()

        for k in list(self.resultsBuf.keys()):
            if k >= matchday:
                self.resultsBuf[k] = ""

        kept = []
        for row in self._rows:
            r = self._parseRow(row)
            if r is None:
                continue
            if r["round"] == THIRD_PLACE_ROUND:
                rowMatchday = self._rounds() - 1 if self._thirdPlaceEnabled() else self._rounds()
            else:
                rowMatchday = self._matchdayForRound(toInt(r["round"]))
            if rowMatchday < matchday:
                kept.append(row)
        self._rows = kept

        if matchday <= 0:
            self._draw = None  # a fresh draw is made when round one is replayed

        self._saveState()
        return dict(self.resumeOpt)
