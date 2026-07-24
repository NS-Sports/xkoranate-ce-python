import math

from ..result import XkorResult
from ..variant import toDouble, toInt, toString
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorLISAParadigm(XkorAbstractH2HParadigm):
    """LISA (Logic Inversion Scorination Algorithm) v1.093.

    Unlike the attack-based paradigms (Footba11er/NSFS/SQIS), LISA decides the
    winner and winning margin first from an Elo-style rank conversion, and
    only afterwards fills in the actual goal totals using style modifiers. It
    therefore overrides generateFTScore/generateETScore/generateSOScore
    directly instead of implementing the generateScore() attack hook that the
    other H2H paradigms share.

    See https://forum.nationstates.net/viewtopic.php?p=42898867#p42898867 and
    the v1.093 update at https://forum.nationstates.net/viewtopic.php?p=43251481#p43251481
    """

    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)

    def hasOptionsWidget(self):
        return True

    def usesMaxSkill(self):
        # _ear() below takes rank as a raw, un-normalized value (see its
        # docstring) and calibrates entirely via refRank/REAR/powerScalar,
        # not via the signup list's generic min/max bounds
        return False

    def usesMinSkill(self):
        return False

    def newAthleteWidget(self):
        from ..signuplisteditor.athletewidget import XkorAthleteWidget
        includeStyle = (toString(self.userOpt.get("styleMods")) != "false"
                        or toString(self.userOpt.get("NSFSStyleMods")) != "false")

        keys = ["name", "nation", "skill"]
        names = ["Participant", "Team", "Skill"]
        types = ["string", "string", "skill"]
        if includeStyle:
            keys.append("style")
            names.append("Style")
            types.append("double")
        if self.perTeamHomeAdvantage():
            keys.append("homeAdvantage")
            names.append("Home Adv")  # matches the reference sheet's own header
            types.append("homeAdvantage")

        return XkorAthleteWidget(keys, names, types, -5, 5, 1)

    def newOptionsWidget(self, paradigmOptions):
        from .options.lisaparadigmoptions import XkorLISAParadigmOptions
        return XkorLISAParadigmOptions(
            paradigmOptions,
            self._defaultHomeAdvantageEAR(),
            self._defaultPowerScalar(),
            self._defaultRefRank(),
            self._defaultREAR(),
            self._defaultMarginDivisor(),
        )

    def _defaultHomeAdvantageEAR(self):
        return toDouble(self.opt.get("homeAdvantageEAR", 100))

    def _defaultPowerScalar(self):
        return toDouble(self.opt.get("powerScalar", 1.984))

    def _defaultRefRank(self):
        return toDouble(self.opt.get("refRank", 10.93))

    def _defaultREAR(self):
        return toDouble(self.opt.get("REAR", 300))

    def _defaultMarginDivisor(self):
        return toDouble(self.opt.get("marginDivisor", 750))

    def homeAdvantageEAR(self):
        # the sport file provides a default magnitude; the options widget
        # lets the user override it per-event
        return toDouble(self.userOpt.get("homeAdvantageEAR", self._defaultHomeAdvantageEAR()))

    def perTeamHomeAdvantage(self):
        """Whether each team's own "Home advantage" rating (entered as a
        participant column, 0-100, defaulting to 50) replaces the fixed
        homeAdvantageEAR() magnitude. Must be set before participants are
        entered since it changes newAthleteWidget()'s columns -- but since
        this is a paradigm option, that's just the natural effect of the
        "Sport" wizard step preceding "Signups"."""
        return toString(self.userOpt.get("perTeamHomeAdvantage")) == "true"

    def powerScalar(self):
        return toDouble(self.userOpt.get("powerScalar", self._defaultPowerScalar()))

    def refRank(self):
        return toDouble(self.userOpt.get("refRank", self._defaultRefRank()))

    def REAR(self):
        return toDouble(self.userOpt.get("REAR", self._defaultREAR()))

    def marginDivisor(self):
        return toDouble(self.userOpt.get("marginDivisor", self._defaultMarginDivisor()))

    # protected: LISA math helpers

    def _ear(self, rank):
        """Rank -> Elo Above Replacement."""
        powerScalar = self.powerScalar()
        refRank = self.refRank()
        rear = self.REAR()
        # derived from REAR so the two values can never drift out of sync
        rankScalar = rear / math.pow(math.log(11.93), powerScalar)
        return rankScalar * math.pow(math.log((rank / refRank * 10.93) + 1), powerScalar)

    def _homeAwayEAR(self, homeAthlete, awayAthlete):
        homeAdvantage = (toString(self.userOpt.get("homeAdvantage")) == "true")
        hEAR = (self._ear(homeAthlete.rpSkill)
                + (self._homeAdvantageValue(homeAthlete, awayAthlete) if homeAdvantage else 0))
        aEAR = self._ear(awayAthlete.rpSkill)
        return hEAR, aEAR

    def _homeAdvantageValue(self, homeAthlete, awayAthlete):
        if self.perTeamHomeAdvantage():
            # each side's own H rating adds to the home team's advantage --
            # a team that sets itself up as a fortress at home gives their
            # opponents the exact same boost when playing away at them
            return self._teamHomeAdvantage(homeAthlete) + self._teamHomeAdvantage(awayAthlete)
        return self.homeAdvantageEAR()

    def _teamHomeAdvantage(self, athlete):
        raw = athlete.property("homeAdvantage")
        return 50.0 if raw in (None, "") else toDouble(raw)

    def _winDrawProbabilities(self, hEAR, aEAR):
        g = hEAR - aEAR
        hxW = 1 / (math.pow(10, -g / 400) + 1)
        axW = 1 / (math.pow(10, g / 400) + 1)
        u = min(hxW, axW)  # underdog win share
        drawP = u - u * u
        underdogWinP = 0.5 * u * u + 0.5 * u
        favouriteWinP = 0.5 * u * u - 1.5 * u + 1
        homeIsUnderdog = (hxW == u)
        homeWinP = underdogWinP if homeIsUnderdog else favouriteWinP
        awayWinP = 1 - drawP - homeWinP
        return drawP, homeWinP, awayWinP

    def _marginLambda(self, gSigned):
        """gSigned is the EAR gap from the eventual winner's perspective
        (negative for an underdog win)."""
        return 1.093 * math.exp(gSigned / self.marginDivisor())

    def _losingScoreLambda(self, netStyle, margin):
        """v1.093-revised losing-team-score lambda: large margins now
        suppress the loser's expected goals instead of being flat."""
        return (1.093 + 0.0984 * netStyle) / math.pow(1 + math.log(max(margin, 1)), 2)

    def _sampleZeroTruncatedPoisson(self, lam):
        rand = self.s.randUniform()
        denom = math.exp(lam) - 1
        acc = 0.0
        k = 1
        pmf = lam / denom  # k=1 term of lam^k / ((e^lam - 1) * k!)
        while True:
            acc += pmf
            if rand < acc or k > 1000:  # safety valve against float drift
                return k
            k += 1
            pmf *= lam / k

    def _samplePoisson(self, lam):
        rand = self.s.randUniform()
        acc = 0.0
        k = 0
        pmf = math.exp(-lam)
        while True:
            acc += pmf
            if rand < acc or k > 1000:
                return k
            k += 1
            pmf *= lam / k

    def _generateMatchScore(self, hEAR, aEAR, netStyle):
        """Runs the win/draw, margin, and losing-score steps of LISA for a
        single period (90 minutes) and returns (homeScore, awayScore)."""
        drawP, homeWinP, _awayWinP = self._winDrawProbabilities(hEAR, aEAR)
        rand = self.s.randUniform()

        if rand < drawP:
            score = self._samplePoisson(self._losingScoreLambda(netStyle, 0))
            return score, score

        homeWins = rand < drawP + homeWinP
        g = (hEAR - aEAR) if homeWins else (aEAR - hEAR)
        margin = self._sampleZeroTruncatedPoisson(self._marginLambda(g))
        losingScore = self._samplePoisson(self._losingScoreLambda(netStyle, margin))
        winningScore = losingScore + margin
        return (winningScore, losingScore) if homeWins else (losingScore, winningScore)

    # protected: paradigm interface

    def generateFTScore(self, home, away):
        hRes = XkorResult()
        aRes = XkorResult()
        hRes.athlete = home.clone()
        aRes.athlete = away.clone()

        hEAR, aEAR = self._homeAwayEAR(home, away)
        netStyle = toDouble(home.property("style")) + toDouble(away.property("style"))

        homeScore, awayScore = self._generateMatchScore(hEAR, aEAR, netStyle)

        hRes.setScore(homeScore)
        aRes.setScore(awayScore)
        return (hRes, aRes)

    def _etDecisiveProbability(self, gAbs):
        """t: probability ET produces a decisive result (no shootout).
        Matches the sheet's CL column exactly: MAX(0.4, ...), not a hard
        cutoff at gAbs=10 (the two are only *approximately* equal there)."""
        return max(0.4, 0.3109 * math.pow(gAbs, 0.1093) + 1 / 10930)

    def _etFavouriteWinProbability(self, t):
        """w: given a decisive ET result, probability the favourite wins."""
        return 0.5 if t == 0.4 else 1.093 * math.pow(t, 0.837)

    def generateETScore(self, home, away, str_):
        home = home.clone()
        away = away.clone()

        hEAR, aEAR = self._homeAwayEAR(home.athlete, away.athlete)
        g = hEAR - aEAR
        gAbs = abs(g)

        t = self._etDecisiveProbability(gAbs)

        scoreType = ("score" if str_ == "" else str_)

        if self.s.randUniform() < t:  # decisive result, i.e. no shootout needed
            w = self._etFavouriteWinProbability(t)
            favouriteIsHome = (hEAR >= aEAR)
            homeWins = (self.s.randUniform() < w) == favouriteIsHome

            netStyle = (toDouble(home.athlete.property("style"))
                        + toDouble(away.athlete.property("style")))
            gWinner = g if homeWins else -g
            # extra time is 1/3 the duration of normal time
            margin = self._sampleZeroTruncatedPoisson(self._marginLambda(gWinner) / 3)
            losingScore = self._samplePoisson(self._losingScoreLambda(netStyle, margin) / 3)
            winningScore = losingScore + margin

            if homeWins:
                home.result[scoreType] = winningScore
                away.result[scoreType] = losingScore
            else:
                home.result[scoreType] = losingScore
                away.result[scoreType] = winningScore
        # if not decisive, leave scoreType unset on both sides so the
        # comparator falls through to the next tiebreaker (shootout)

        return (home, away)

    def generateSOScore(self, home, away, str_):
        """Qusma shootout algorithm: rank-independent, tiered conversion
        probabilities (3/4 for kicks 1-3, 2/3 for kicks 4-10, 1/2 for kick
        11 onward as sudden death)."""
        home = home.clone()
        away = away.clone()
        pkCount = 10  # regulation kicks (3 @ 3/4 + 7 @ 2/3) before sudden death

        def kickProb(kickNumber):  # 1-based
            if kickNumber <= 3:
                return 3 / 4
            elif kickNumber <= 10:
                return 2 / 3
            else:
                return 1 / 2

        count = 0
        while abs(toInt(home.value(str_)) - toInt(away.value(str_))) <= pkCount - count:
            p = kickProb(count + 1)
            if self.s.randUniform() < p:
                home.result[str_] = toInt(home.value(str_)) + 1
            if self.s.randUniform() < p:
                away.result[str_] = toInt(away.value(str_)) + 1
            if count >= pkCount:
                count -= 1
            count += 1

        return (home, away)
