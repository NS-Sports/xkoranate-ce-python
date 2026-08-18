"""The "otWins" sort criterion, offered as "Overtime/shootout wins".

Despite the name it counts wins from both extra time and shootouts, matching
the single sort-rule entry the two share — a league that wants them separated
ranks on "Regulation wins" instead. The criterion keeps its "otWins" key
because that string is what already-saved table files store.
"""


class XkorSortOTWinsGr:
    def __call__(self, a, b):
        return a.otWins() + a.soWins() > b.otWins() + b.soWins()


class XkorSortOTWinsEq:
    def __call__(self, a, b):
        return a.otWins() + a.soWins() == b.otWins() + b.soWins()
