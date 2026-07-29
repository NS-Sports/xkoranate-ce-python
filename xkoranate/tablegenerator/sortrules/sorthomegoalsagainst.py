class XkorSortHomeGoalsAgainstGr:
    def __call__(self, a, b):
        return a.homeGoalsAgainst() < b.homeGoalsAgainst()


class XkorSortHomeGoalsAgainstEq:
    def __call__(self, a, b):
        return a.homeGoalsAgainst() == b.homeGoalsAgainst()
