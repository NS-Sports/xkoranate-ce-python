import math

from ..variant import toDouble, toInt
from .abstracth2hparadigm import XkorAbstractH2HParadigm


class XkorNSFSParadigm(XkorAbstractH2HParadigm):
    _nsfsStyleModsDefault = "true"

    def newOptionsWidget(self, paradigmOptions):
        from .options.nsfsparadigmoptions import XkorNSFSParadigmOptions
        return XkorNSFSParadigmOptions(
            paradigmOptions,
            self._defaultHomeAdvantageMagnitude(),
            self._defaultBaseAttackCoeff(),
            self._defaultRankDiffModifier(),
            self._defaultRankCoeff(),
            self._defaultRankScalar(),
            self._defaultBaseAttackSuccessThreshold(),
            self._defaultBaseAttacksSuperior(),
            self._defaultBaseAttacksInferior(),
            self._defaultAttackCoeffSuperior(),
            self._defaultAttackCoeffInferior(),
        )

    def _defaultBaseAttackCoeff(self):
        return toDouble(self.opt.get("baseAttackCoeff", 667.5))

    def _defaultRankDiffModifier(self):
        return toDouble(self.opt.get("rankDiffModifier", 12))

    def _defaultRankCoeff(self):
        return toDouble(self.opt.get("rankCoeff", 31.5))

    def _defaultRankScalar(self):
        return toDouble(self.opt.get("rankScalar", 0.5))

    def _defaultBaseAttackSuccessThreshold(self):
        return toDouble(self.opt.get("baseAttackSuccessThreshold", 580))

    def _defaultBaseAttacksSuperior(self):
        return toDouble(self.opt.get("baseAttacksSuperior", 10))

    def _defaultBaseAttacksInferior(self):
        return toDouble(self.opt.get("baseAttacksInferior", 10))

    def _defaultAttackCoeffSuperior(self):
        return toDouble(self.opt.get("attackCoeffSuperior", 10))

    def _defaultAttackCoeffInferior(self):
        return toDouble(self.opt.get("attackCoeffInferior", 0))

    def baseAttackCoeff(self):
        return toDouble(self.userOpt.get("baseAttackCoeff", self._defaultBaseAttackCoeff()))

    def rankDiffModifier(self):
        return toDouble(self.userOpt.get("rankDiffModifier", self._defaultRankDiffModifier()))

    def rankCoeff(self):
        return toDouble(self.userOpt.get("rankCoeff", self._defaultRankCoeff()))

    def rankScalar(self):
        return toDouble(self.userOpt.get("rankScalar", self._defaultRankScalar()))

    def baseAttackSuccessThreshold(self):
        return toDouble(self.userOpt.get(
            "baseAttackSuccessThreshold", self._defaultBaseAttackSuccessThreshold()))

    def baseAttacksSuperior(self):
        return toInt(self.userOpt.get("baseAttacksSuperior", self._defaultBaseAttacksSuperior()))

    def baseAttacksInferior(self):
        return toInt(self.userOpt.get("baseAttacksInferior", self._defaultBaseAttacksInferior()))

    def attackCoeffSuperior(self):
        return toDouble(self.userOpt.get("attackCoeffSuperior", self._defaultAttackCoeffSuperior()))

    def attackCoeffInferior(self):
        return toDouble(self.userOpt.get("attackCoeffInferior", self._defaultAttackCoeffInferior()))

    # protected:

    def generateScore(self, skill, oppSkill, style, oppStyle,
                      homeAdvantage=False, attackMultiplier=1):
        # load constants
        baseAttackCoeff = self.baseAttackCoeff()
        rankDiffModifier = self.rankDiffModifier()
        rankCoeff = self.rankCoeff()
        rankScalar = self.rankScalar()
        bast = self.baseAttackSuccessThreshold()
        baseAttacksSuperior = self.baseAttacksSuperior()
        baseAttacksInferior = self.baseAttacksInferior()
        attackCoeffSuperior = self.attackCoeffSuperior()
        attackCoeffInferior = self.attackCoeffInferior()
        homeAdvValue = (self.homeAdvantageMagnitude() if homeAdvantage else 1)

        if skill > oppSkill:
            attacks = int((baseAttacksSuperior + ((skill - oppSkill) * attackCoeffSuperior))
                          * attackMultiplier)
        else:
            attacks = int((baseAttacksInferior + ((skill - oppSkill) * attackCoeffInferior))
                          * attackMultiplier)

        # calculate P(goal) on any given attack
        pGoal = 1 - ((bast + rankDiffModifier
                      * (math.pow(oppSkill * rankCoeff, rankScalar)
                         - math.pow(skill * rankCoeff, rankScalar)))
                     / (baseAttackCoeff * homeAdvValue))

        # score
        return self._binomialDraw(attacks, pGoal)
