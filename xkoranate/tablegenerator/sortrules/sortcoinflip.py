import random

# a flip is saved through qNumber(), which writes 6 significant digits — so it
# has to be a whole number below a million to reload as the value that was
# written. Two teams sharing a value would tie in the sort that's meant to be
# the last resort, so values are drawn without repeats rather than trusted to
# be distinct by luck.
_MAX_FLIP = 999999


def assignCoinFlips(rows, coinFlips):
    """Give every row in `rows` a coin-flip value in `coinFlips` (keyed by
    team name), flipping a fresh one only the first time a team is seen.
    `coinFlips` is mutated in place and is expected to be the table's own
    persisted store, so a team's flip result — once made — sticks for as
    long as the table file does, surviving regenerating the table or
    relaunching the app, the same way a real coin toss wouldn't be redone
    just because someone looked at the standings again."""
    taken = set(coinFlips.values())
    for r in rows:
        if r.name() not in coinFlips:
            value = random.randint(0, _MAX_FLIP)
            while value in taken:
                value = random.randint(0, _MAX_FLIP)
            coinFlips[r.name()] = value
            taken.add(value)


def pruneCoinFlips(teamNames, coinFlips):
    """Drop flips for teams the table no longer has, so renaming a team over
    and over doesn't grow the saved file without bound. Mutates in place."""
    teamNames = set(teamNames)
    for name in [n for n in coinFlips if n not in teamNames]:
        del coinFlips[name]


class XkorSortCoinFlipGr:
    def __init__(self, coinFlips):
        self.coinFlips = coinFlips

    def __call__(self, a, b):
        return self.coinFlips[a.name()] > self.coinFlips[b.name()]


class XkorSortCoinFlipEq:
    def __init__(self, coinFlips):
        self.coinFlips = coinFlips

    def __call__(self, a, b):
        return self.coinFlips[a.name()] == self.coinFlips[b.name()]
