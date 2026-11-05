from ..variant import toDouble


class XkorPointByPointMixin:
    """For paradigms that play a match one point (or game) at a time, each
    going to the side with the better weighted draw plus a random attack
    bonus."""

    def generatePointScore(self, homeSkill, awaySkill):
        attackModifier = toDouble(self.opt.get("attackModifier"))

        first = self.s.randWeightedH2H(homeSkill, awaySkill) + self.s.randUniform() * attackModifier
        second = self.s.randWeightedH2H(awaySkill, homeSkill) + self.s.randUniform() * attackModifier

        return (first, second)

    def formatScore(self, score1, score2):
        return str(score1) + "–" + str(score2)
