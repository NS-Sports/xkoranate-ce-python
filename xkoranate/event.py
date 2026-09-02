from .athlete import BYE_ID, makeBye
from .exceptions import XkorSearchFailedException
from .signuplist import XkorSignupList
from .startlist import XkorStartList, XkorStartListGroup


class XkorEvent:
    def __init__(self):
        self.m_competition = ""
        self.m_competitionOptions = {}
        self.m_name = ""
        self.m_groups = []  # list of XkorGroup
        self.m_paradigm = ""
        self.m_paradigmOptions = {}
        self.m_results = {}  # matchday (int) -> result text
        self.m_signupList = XkorSignupList()
        self.m_sport = ""

    def competition(self):
        return self.m_competition

    def competitionOptions(self):
        return dict(self.m_competitionOptions)

    def groups(self):
        return list(self.m_groups)

    def makeStartList(self, rpList):
        rval = XkorStartList()
        ubersignuplist = XkorSignupList()

        # make signup lists for each file and dump athletes into the übersignuplist
        for i in self.m_signupList.athletes():
            ath = i.clone()
            ath.skill = self.m_signupList.adjustRank(ath.skill)
            ubersignuplist.addAthlete(ath)

        # now create the start list
        maxRPSkill = 0.0
        for i in self.m_groups:
            currentGroup = XkorStartListGroup()
            for j in i.athletes:
                if j == BYE_ID:
                    # a bye carries no skill and takes no RP bonus; it exists
                    # only to hold a slot in a knockout draw
                    currentGroup.athletes.append(makeBye())
                    continue
                try:
                    a = ubersignuplist.getAthleteByID(j).clone()
                    if rpList is not None:
                        if rpList.useTeams():
                            a.rpBonus = rpList.bonus(a.nation)
                        else:
                            a.rpBonus = rpList.bonus(a.name)
                        if rpList.useWGStyleBonus():
                            a.rpSkill = a.skill + a.rpBonus * (100 / (100 - rpList.rpEffect()) - 1)
                            if a.rpSkill > maxRPSkill:
                                maxRPSkill = a.rpSkill
                        else:
                            a.rpSkill = (a.rpBonus * (rpList.rpEffect() / 100)
                                         + a.skill * (1 - (rpList.rpEffect() / 100)))
                    else:
                        a.rpSkill = a.skill
                    currentGroup.athletes.append(a)
                except XkorSearchFailedException:
                    pass
            currentGroup.name = i.name
            rval.groups.append(currentGroup)

        # now scale back the bonuses if any are too high in WG style
        if rpList is not None and rpList.useWGStyleBonus() and maxRPSkill > 1:
            for i in rval.groups:
                for j in i.athletes:
                    j.rpSkill /= maxRPSkill

        # copy over settings from the event
        rval.name = self.m_name
        return rval

    def name(self):
        return self.m_name

    def paradigm(self):
        return self.m_paradigm

    def paradigmOptions(self):
        return dict(self.m_paradigmOptions)

    def results(self):
        return dict(self.m_results)

    def signupList(self):
        return self.m_signupList

    def sport(self):
        return self.m_sport

    def addGroup(self, group):
        self.m_groups.append(group)

    def replaceCompetitionOptions(self, competitionOptions):
        # clear the old values, then set the new values
        for k in competitionOptions:
            self.m_competitionOptions.pop(k, None)
        for k, v in competitionOptions.items():
            self.m_competitionOptions[k] = v

    def setCompetition(self, competition):
        self.m_competition = competition

    def setCompetitionOptions(self, competitionOptions):
        self.m_competitionOptions = competitionOptions

    def setGroups(self, groups):
        self.m_groups = groups

    def setName(self, name):
        self.m_name = name

    def setParadigmOptions(self, paradigmOptions):
        self.m_paradigmOptions = paradigmOptions

    def setResult(self, matchday, result):
        self.m_results[matchday] = result
        # if we've backtracked, make sure we don't have any residual "future" results
        for k in list(self.m_results.keys()):
            if k > matchday:
                self.m_results[k] = ""

    def setResults(self, results):
        self.m_results = results

    def setSignupList(self, signupList):
        self.m_signupList = signupList

    def setSport(self, sport, newParadigm=""):
        self.m_sport = sport
        self.m_paradigm = newParadigm
