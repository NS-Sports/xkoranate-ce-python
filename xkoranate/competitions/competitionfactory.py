from xkoranate.competitions.archerycompetition import XkorArcheryCompetition
from xkoranate.competitions.matchescompetition import XkorMatchesCompetition
from xkoranate.competitions.multipleruncompetition import XkorMultipleRunCompetition
from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition
from xkoranate.competitions.shootingcompetition import XkorShootingCompetition
from xkoranate.competitions.singleeliminationcompetition import XkorSingleEliminationCompetition
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
        elif type == "shooting":
            rval = XkorShootingCompetition()
        elif type == "singleElimination":
            rval = XkorSingleEliminationCompetition()
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
        rval["shooting"] = "Shooting competition"
        rval["singleElimination"] = "Single elimination"
        rval["standard"] = "Mass start"
        rval["roundRobin"] = "Round robin"
        return rval
