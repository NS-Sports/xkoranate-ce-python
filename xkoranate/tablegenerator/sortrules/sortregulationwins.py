class XkorSortRegulationWinsGr:
    def __call__(self, a, b):
        return a.regulationWins() > b.regulationWins()


class XkorSortRegulationWinsEq:
    def __call__(self, a, b):
        return a.regulationWins() == b.regulationWins()
