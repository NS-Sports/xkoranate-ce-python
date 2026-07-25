import random


def assignCoinFlips(rows, coinFlips):
    """Give every row in `rows` a coin-flip value in `coinFlips` (keyed by
    team name), flipping a fresh one only the first time a team is seen.
    `coinFlips` is mutated in place and is expected to be the table's own
    persisted store, so a team's flip result — once made — sticks for as
    long as the table file does, surviving regenerating the table or
    relaunching the app, the same way a real coin toss wouldn't be redone
    just because someone looked at the standings again."""
    for r in rows:
        if r.name() not in coinFlips:
            coinFlips[r.name()] = random.random()


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
