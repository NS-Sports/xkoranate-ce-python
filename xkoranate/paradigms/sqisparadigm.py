from ..variant import toDouble
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorSQISParadigm(XkorAbstractH2HParadigm):
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

    def _defaultConstantA(self):
        return toDouble(self.opt.get("constantA", 0.1))

    def _defaultConstantB(self):
        return toDouble(self.opt.get("constantB", 0.07))

    def _defaultAttacks(self):
        return toDouble(self.opt.get("attacks", 12))

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
        return self._binomialDraw(attacks, pGoal)
