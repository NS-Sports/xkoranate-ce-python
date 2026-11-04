import sys

from ..athlete import XkorAthlete
from ..result import XkorResult
from ..variant import toDouble, toInt, toList, toString
from .comparators.basicresultcomparator import XkorBasicResultComparator


class XkorAbstractParadigm:
    def __init__(self, sport=None, userOptions=None):
        super().__init__()
        self.s = None
        self.supportedCompetitions = {}  # QHash<QString, bool>
        self.opt = {}
        self.userOpt = {}
        self.requiredValues = []  # QStringList
        self.res = []  # QVector<XkorResult>
        self.out = []  # QList<QPair<QString, QString> > — list of 2-tuples
        if sport is not None:
            self.init(sport, userOptions)

    def addResults(self, previousResults):
        for i in previousResults:
            r = i.clone()
            r.setOutput(self.outputLine(r))
            self.res.append(r)

    def breakTie(self, athletes, type=""):
        return  # tell whoever’s requesting a tiebreaker to stuff it

    def compare(self, a, b, type=""):
        f = self.comparisonFunction(type)
        if f(a, b):  # if(a < b)
            return -1
        elif f(b, a):  # if(b < a)
            return 1
        else:
            return 0

    def comparisonFunction(self, type=""):
        return XkorBasicResultComparator(type, self.opt)

    def defaultCompetition(self):
        return "standard"

    def findResult(self, id):
        """Returns the matching XkorResult in res, or None (C++ returned
        res.end())."""
        for i in self.res:
            if i.athlete.id == id:
                return i
        return None

    def hasOptionsWidget(self):
        return True

    def usesMaxSkill(self):
        """Whether the signup list's "Maximum skill" bound actually affects
        this paradigm's results. Most paradigms compare skill to a fixed
        reference (rank power curve, absolute attack coefficients, etc.), so
        rescaling the whole population by a different max changes outcomes.
        A handful (SQIS, Footba11er, Howzzat) only ever compare one
        athlete's skill to their specific opponent's as a plain ratio, which
        is invariant to any common rescale — see their own overrides."""
        return True

    def usesMinSkill(self):
        """Whether the signup list's "Minimum skill" bound actually affects
        this paradigm's results. False only for paradigms that need raw,
        un-normalized rank as input and calibrate entirely through their own
        formula constants instead (see LISA's override)."""
        return True

    def init(self, sport, userOptions):
        self.s = sport
        self.userOpt = userOptions
        self.opt = sport.paradigmOptions()

    def newAthleteWidget(self):
        from ..signuplisteditor.athletewidget import XkorAthleteWidget
        return XkorAthleteWidget(["name", "nation", "skill"],
                                 ["Participant", "Team", "Skill"],
                                 ["string", "string", "skill"])

    def newOptionsWidget(self, paradigmOptions):
        from .options.timedparadigmoptions import XkorTimedParadigmOptions
        return XkorTimedParadigmOptions(paradigmOptions)

    def output(self):
        rval = ""
        for i in self.out:
            rval += i[1] + "\n"
        return rval

    def option(self, key):
        return self.opt.get(key)

    def results(self):
        return list(self.res)

    def scorinate(self, athletes, previousResults=None):
        raise NotImplementedError

    def supportsCompetition(self, competition):
        # A knockout asks a paradigm for exactly what an individual-matches
        # competition asks: scorinate a pair, compare and break the tie,
        # output the line. So anything that can run "matches" can run a
        # bracket, and deriving that here keeps the two from drifting — the
        # five places that declared singleElimination by hand had already
        # missed archery and parallel giant slalom, the latter a sport
        # actually run as a knockout. A paradigm can still opt out by
        # declaring the key False.
        if competition == "singleElimination" \
                and "singleElimination" not in self.supportedCompetitions:
            competition = "matches"
        # likewise a conference league is round robins played across groups
        # as well as within them, so it needs nothing a round robin doesn't
        if competition == "interConference" \
                and "interConference" not in self.supportedCompetitions:
            competition = "roundRobin"
        return self.supportedCompetitions.get(competition, False)

    # protected:

    def individualResult(self, athlete, type):
        return XkorResult(0, ath=athlete)

    # helper functions for subclasses
    def _checkRequiredValues(self, where):
        """False, after noting it in the output, if the sport lacks a
        value this paradigm needs; `where` names the caller for stderr."""
        for i in self.requiredValues:
            if not self.s.hasValue(i):
                print("missing parameter", i, "in " + where, file=sys.stderr)
                self.out.append(("", "Sport does not support this paradigm"))
                return False
        return True

    def _adjustSkill(self, realSkill, prefix):
        """Skill blurred by the sport's <prefix>RankModifier and
        <prefix>RankAdjustmentFactor options."""
        rankModifier = toDouble(self.opt.get(prefix + "RankModifier", 0))
        rankAdjustmentFactor = toDouble(self.opt.get(prefix + "RankAdjustmentFactor", 1))

        # randomize the skill a bit to compensate for the fact that long
        # sequences of arrows would otherwise be highly predictable
        rval = (realSkill + self.s.randUniform() * rankModifier) / (1 + rankModifier)
        rval = rval * rankAdjustmentFactor + (1 - rankAdjustmentFactor) / 2
        return rval

    @staticmethod
    def _pairs(athletes):
        """(home, away) for each match in a list laid out home, away,
        home, away…; an odd athlete out at the end is skipped."""
        for awayIdx in range(1, len(athletes), 2):
            yield athletes[awayIdx - 1], athletes[awayIdx]

    def formatName(self, name, nation=None):
        # collapses the C++ overloads formatName(QString, QString) and
        # formatName(XkorAthlete)
        if isinstance(name, XkorAthlete):
            ath = name
            return self.formatName(ath.name, ath.nation)
        if toString(self.userOpt.get("showTLAs", "true")) == "true" and nation:
            return name + " (" + nation + ")"
        else:
            return name

    def _worstScore(self):
        """The score that sorts last under the sport's sort order; its
        negation sorts first."""
        return (sys.float_info.max
                if toString(self.opt.get("sortOrder", "ascending")) == "ascending"
                else -sys.float_info.max)

    def generateStatus(self):
        statuses = self.readOptionList("statuses")
        statusProbs = self.readOptionList("statusProbs")

        rand = self.s.randUniform()

        acc = 0.0
        for i in range(len(statuses)):
            acc += toDouble(statusProbs[i])
            if rand < acc:
                return toString(statuses[i])
        return ""

    def generateOutput(self):
        self.out = []
        for i in self.res:
            if i.output() != "":
                self.out.append((i.athlete.name, i.output()))

    def outputLine(self, r):
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 10)) + 2

        rval = self.formatName(r.athlete.name, r.athlete.nation).ljust(nameWidth)
        rval += r.scoreString().rjust(resultWidth)

        return rval

    def readOptionList(self, name):
        if name in self.opt:
            val = self.opt[name]
            if isinstance(val, list):
                return toList(val)
            else:
                return [val]  # create a single-item list
        else:
            # this is important, we don’t want to trick the paradigm into
            # thinking there’s a value when there isn’t one
            return []

    def timeFormat(self, n, displayDigits):
        rval = ""

        if n > 3600:  # hours
            rval += str(int(n / 3600))
            rval += ":"
            if int(n) % 3600 < 600:  # need a leading zero for minutes
                rval += "0"
        if n > 60:  # minutes
            rval += str(int(n / 60) % 60)
            rval += ":"
            if int(n) % 60 < 10:  # need a leading zero for seconds
                rval += "0"
        rval += f"{n - int(n / 60) * 60:.{displayDigits}f}"
        return rval
