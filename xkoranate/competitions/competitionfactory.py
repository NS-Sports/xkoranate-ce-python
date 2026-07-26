from xkoranate.competitions.archerycompetition import XkorArcheryCompetition
from xkoranate.competitions.matchescompetition import XkorMatchesCompetition
from xkoranate.competitions.multipleruncompetition import XkorMultipleRunCompetition
from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition
from xkoranate.competitions.seasoncompetition import XkorSeasonCompetition
from xkoranate.competitions.shootingcompetition import XkorShootingCompetition
from xkoranate.competitions.singleracecompetition import XkorSingleRaceCompetition
from xkoranate.competitions.standardcompetition import XkorMassStartCompetition


class XkorCompetitionFactory:
    @staticmethod
    def newCompetition(type):
        if type == "standard":
            rval = XkorMassStartCompetition()
        elif type == "archery":
            rval = XkorArcheryCompetition()
        elif type == "matches":
            rval = XkorMatchesCompetition()
        elif type == "multipleRun":
            rval = XkorMultipleRunCompetition()
        elif type == "roundRobin":
            rval = XkorRoundRobinCompetition()
        elif type == "season":
            rval = XkorSeasonCompetition()
        elif type == "shooting":
            rval = XkorShootingCompetition()
        elif type == "singleRace":
            rval = XkorSingleRaceCompetition()
        else:
            rval = XkorRoundRobinCompetition()
        return rval

    @staticmethod
    def newCompetitionFull(type, sl, s, paradigmOptions, competitionOptions, results):
        rval = XkorCompetitionFactory.newCompetition(type)
        rval.init(sl, s, paradigmOptions, competitionOptions, results)
        return rval

    @staticmethod
    def competitionTypes():
        rval = {}
        rval["archery"] = "Archery ranking round"
        rval["matches"] = "Individual matches"
        rval["multipleRun"] = "Multiple-run competition"
        rval["season"] = "Racing season"
        rval["shooting"] = "Shooting competition"
        rval["singleRace"] = "Single race"
        rval["standard"] = "Mass start"
        rval["roundRobin"] = "Round robin"
        return rval
