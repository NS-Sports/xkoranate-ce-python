class XkorRPList:
    def __init__(self):
        self.m_competitionName = ""
        self.bon = {}  # code -> {property -> double}
        self.rpCalcType = "olympic"
        self.rpOpts = {}
        self.max = 1.0
        self.min = 0.0
        self.eff = 15.0
        self.teams = True

    def addBonus(self, properties):
        # properties is a (code, {property: value}) pair
        self.bon[properties[0]] = properties[1]

    def bonus(self, code):
        return (self.bon.get(code, {}).get("bonus", 0.0) - self.min) / (self.max - self.min)

    def bonuses(self):
        return dict(self.bon)

    def clone(self):
        # passed by value in the C++
        rval = XkorRPList()
        rval.m_competitionName = self.m_competitionName
        rval.bon = {k: dict(v) for k, v in self.bon.items()}
        rval.rpCalcType = self.rpCalcType
        rval.rpOpts = dict(self.rpOpts)
        rval.max = self.max
        rval.min = self.min
        rval.eff = self.eff
        rval.teams = self.teams
        return rval

    def competitionName(self):
        return self.m_competitionName

    def maxBonus(self):
        return self.max

    def minBonus(self):
        return self.min

    def rpCalculationType(self):
        return self.rpCalcType

    def rpEffect(self):
        return self.eff

    def rpOptions(self):
        return dict(self.rpOpts)

    def useTeams(self):
        return self.teams

    def useWGStyleBonus(self):
        return self.rpCalcType == "relative"

    def setBonuses(self, newBonuses):
        self.bon = newBonuses

    def setCompetitionName(self, newName):
        self.m_competitionName = newName

    def setMaxBonus(self, newMax):
        self.max = newMax

    def setMinBonus(self, newMin):
        self.min = newMin

    def setRPCalculationType(self, newType):
        self.rpCalcType = newType

    def setRPEffect(self, newEffect):
        self.eff = newEffect

    def setRPOptions(self, newOpts):
        self.rpOpts = newOpts

    def setUseTeams(self, newValue):
        self.teams = newValue
