from ..variant import toInt
from .timedparadigm import XkorTimedParadigm


class XkorScoredParadigm(XkorTimedParadigm):
    # private:

    def formatScore(self, score):
        return f"{score:.{toInt(self.opt.get('displayDigits'))}f}"
