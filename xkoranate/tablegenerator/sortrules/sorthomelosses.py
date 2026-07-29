class XkorSortHomeLossesGr:
    def __call__(self, a, b):
        return a.homeLosses() < b.homeLosses()


class XkorSortHomeLossesEq:
    def __call__(self, a, b):
        return a.homeLosses() == b.homeLosses()
