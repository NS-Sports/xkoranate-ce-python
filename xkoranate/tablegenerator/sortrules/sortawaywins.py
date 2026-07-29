class XkorSortAwayWinsGr:
    def __call__(self, a, b):
        return a.awayWins() > b.awayWins()


class XkorSortAwayWinsEq:
    def __call__(self, a, b):
        return a.awayWins() == b.awayWins()
