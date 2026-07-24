class XkorSortOTWinsGr:
    def __call__(self, a, b):
        return a.otWins() + a.soWins() > b.otWins() + b.soWins()


class XkorSortOTWinsEq:
    def __call__(self, a, b):
        return a.otWins() + a.soWins() == b.otWins() + b.soWins()
