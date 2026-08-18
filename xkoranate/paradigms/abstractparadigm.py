from PySide6.QtCore import QObject

from ..athlete import XkorAthlete
from ..result import XkorResult
from ..variant import toInt, toList, toString
from .comparators.basicresultcomparator import XkorBasicResultComparator


class XkorAbstractParadigm(QObject):
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
        return False

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
        return None

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
        return self.supportedCompetitions.get(competition, False)

    # protected:

    def individualResult(self, athlete, type):
        return XkorResult(0, ath=athlete)

    # helper functions for subclasses
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
