import math

from ..variant import toDouble
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorSQISParadigm(XkorAbstractH2HParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)

    def hasOptionsWidget(self):
        return True

    def usesMaxSkill(self):
        # generateScore() below only ever compares min(skill,oppSkill) /
        # max(skill,oppSkill) between the two specific competitors, which is
        # invariant to any common rescale of the whole population
        return False

    def newOptionsWidget(self, paradigmOptions):
        from .options.sqisparadigmoptions import XkorSQISParadigmOptions
        return XkorSQISParadigmOptions(
            paradigmOptions,
            self._defaultHomeAdvantageMagnitude(),
            self._defaultConstantA(),
            self._defaultConstantB(),
            self._defaultAttacks(),
        )

    def _defaultHomeAdvantageMagnitude(self):
        return toDouble(self.opt.get("homeAdvantage", 4.0 / 3.0))

    def _defaultConstantA(self):
        return toDouble(self.opt.get("constantA", 0.1))

    def _defaultConstantB(self):
        return toDouble(self.opt.get("constantB", 0.07))

    def _defaultAttacks(self):
        return toDouble(self.opt.get("attacks", 12))

    def homeAdvantageMagnitude(self):
        # the sport file provides a default magnitude; the options widget
        # lets the user override it per-event
        return toDouble(self.userOpt.get("homeAdvantageMagnitude", self._defaultHomeAdvantageMagnitude()))

    def constantA(self):
        return toDouble(self.userOpt.get("constantA", self._defaultConstantA()))

    def constantB(self):
        return toDouble(self.userOpt.get("constantB", self._defaultConstantB()))

    def baseAttacks(self):
        return toDouble(self.userOpt.get("attacks", self._defaultAttacks()))

    # protected:

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        # add 0.5 so that values can be rounded up
        attacks = int(self.baseAttacks() * attackMultiplier + 0.5)

        a = self.constantA()
        b = self.constantB()
        homeAdvValue = (self.homeAdvantageMagnitude() if homeAdvantage else 1)

        # calculate P(goal) on any given attack
        pGoal = (a + (b - (1 if skill == oppSkill else min(skill, oppSkill) / max(skill, oppSkill)) * b)
                 * (1 if skill > oppSkill else -1)) * homeAdvValue

        # score
        rand = self.s.randUniform()
        acc = 0.0
        pIGoals = math.pow(1 - pGoal, attacks)  # probability of 0 goals
        for i in range(attacks + 1):
            acc += pIGoals
            if rand < acc:
                return i
            # calculate probability of i + 1 goals
            pIGoals *= (attacks - i) * pGoal / ((i + 1) * (1 - pGoal))
        return -1
