"""Draw and seeding helpers for single-elimination brackets.

A bracket is a flat list of slots whose length is a power of two. Slots
2m and 2m+1 make up match m of the first round; the winners of matches
2m and 2m+1 make up match m of the next round, and so on. An empty slot
(``None``) is a bye: its partner advances unopposed.

Ported from the Google Apps Script prototypes attached to issue #22
(``knockout_draws.gs``, ``pot_utils.gs``, ``qusma_seeding.gs``).
"""

import math

from xkoranate.athlete import isBye

MANUAL = "manual"
RANDOM = "random"
SEEDED = "seeded"
VARIABLE_SEEDS = "variableSeeds"

SEEDING_METHODS = [MANUAL, RANDOM, SEEDED, VARIABLE_SEEDS]


def bracketSize(n):
    """Smallest power of two that holds n entrants (at least 2)."""
    if n <= 2:
        return 2
    return 2 ** int(math.ceil(math.log2(n)))


def standardSeedOrder(n):
    """Seed numbers in slot order for a bracket of n slots.

    standardSeedOrder(8) == [1, 8, 4, 5, 2, 7, 3, 6], i.e. 1 v 8 in the
    first match and 4 v 5 in the second, so every match's seeds sum to
    n + 1 and the top two can only meet in the final. n must be a power
    of two.
    """
    seeds = [1]
    while len(seeds) < n:
        next_ = []
        for s in seeds:
            next_.append(s)
            next_.append(2 * len(seeds) + 1 - s)
        seeds = next_
    return seeds


def matchOf(slot):
    """The match a slot belongs to, within its round."""
    return slot // 2


def partnerOf(slot):
    """The other slot in the same match."""
    return slot ^ 1


def byeSlots(size, count, seedOrder=None, rng=None):
    """Pick `count` slots to leave empty, one per match.

    Byes are given to the partners of the strongest seeds, so the top of
    the bracket gets the free passage. With no seed order the slots are
    chosen at random instead — but still one per match, because a match
    with two empty slots has nobody to advance.
    """
    if count <= 0:
        return []
    if count > size // 2:
        raise ValueError("cannot place %d byes in a %d-slot bracket" % (count, size))

    if seedOrder is None:
        matches = list(range(size // 2))
        if rng is not None:
            rng.shuffle(matches)
        # the empty slot within each chosen match is arbitrary; take the away side
        return sorted(2 * m + 1 for m in matches[:count])

    # score each slot by how strong its partner is, then hand the byes to
    # the slots facing the strongest seeds (qusma_seeding.gs byeCandidates)
    candidates = sorted(range(size), key=lambda i: (seedOrder[partnerOf(i)], i))
    chosen = []
    usedMatches = set()
    for slot in candidates:
        if len(chosen) == count:
            break
        if matchOf(slot) in usedMatches:
            continue
        usedMatches.add(matchOf(slot))
        chosen.append(slot)
    return sorted(chosen)


def _emptyBracket(size, byes):
    bracket = [None] * size
    reserved = set(byes)
    return bracket, reserved


def _freeSlots(bracket, reserved):
    return [i for i in range(len(bracket)) if bracket[i] is None and i not in reserved]


def drawManual(entrants, size):
    """Read the bracket straight off the entrant order, with no randomness.

    The first entrants in the list take the byes — the usual convention,
    and the one the user can see and control by reordering the group.
    Everyone else pairs off two at a time down the bracket.
    """
    byes = size - len(entrants)
    # byes go to the top matches so that the head of the list gets them
    byeSlotList = [2 * m + 1 for m in range(byes)]
    bracket, reserved = _emptyBracket(size, byeSlotList)

    pool = list(entrants)
    for slot in _freeSlots(bracket, reserved):
        if not pool:
            break
        bracket[slot] = pool.pop(0)
    return bracket


def drawRandom(entrants, size, rng):
    """Shuffle the entrants and pair them off (drawCupRoundSimple)."""
    byes = size - len(entrants)
    bracket, reserved = _emptyBracket(size, byeSlots(size, byes, rng=rng))

    pool = list(entrants)
    if rng is not None:
        rng.shuffle(pool)
    for slot in _freeSlots(bracket, reserved):
        if not pool:
            break
        bracket[slot] = pool.pop(0)
    return bracket


def _bySkill(entrants):
    """Entrants strongest first. Stable, so equal skills keep list order."""
    return sorted(entrants, key=lambda a: -a.skill)


def drawSeeded(entrants, size, rng=None):
    """Standard seeded bracket: 1 v size, 2 v size-1, and so on."""
    seeds = _bySkill(entrants)
    seedOrder = standardSeedOrder(size)
    byes = size - len(seeds)
    bracket, reserved = _emptyBracket(size, byeSlots(size, byes, seedOrder))

    # slot i is contested by seed seedOrder[i]; fill in seed order so that
    # a slot reserved for a bye pushes the remaining seeds down by one
    remaining = list(seeds)
    for slot in sorted(range(size), key=lambda i: seedOrder[i]):
        if slot in reserved:
            continue
        if not remaining:
            break
        bracket[slot] = remaining.pop(0)
    return bracket


def drawVariableSeeds(entrants, size, numSeeds, rng):
    """Spread the top `numSeeds` entrants across the bracket, draw the rest.

    Ports drawCupRoundVariableSeeds(): seeds are placed at even intervals
    in standard seed order, and the unseeded pool is shuffled into the gaps.
    """
    ranked = _bySkill(entrants)
    numSeeds = max(0, min(numSeeds, len(ranked)))
    if numSeeds <= 1:
        # nothing to keep apart; a single seed is just a random draw
        return drawRandom(entrants, size, rng)

    byes = size - len(ranked)
    if byes > size // 2:
        raise ValueError("cannot place %d byes in a %d-slot bracket" % (byes, size))

    seeds = ranked[:numSeeds]
    pool = ranked[numSeeds:]
    if rng is not None:
        rng.shuffle(pool)

    bracket = [None] * size
    seededMatches = set()
    slotOfSeed = {}

    # Place the seeds at evenly spaced target slots. The walk skips any match
    # that already holds a seed, not merely any occupied slot: putting two
    # seeds in one match is the one thing this draw exists to prevent, and
    # checking only the slot let a seed displaced off a reserved slot land
    # opposite its neighbour.
    placementOrder = [s for s in standardSeedOrder(bracketSize(numSeeds)) if s <= numSeeds]
    for index, seedRank in enumerate(placementOrder):
        target = int(round(index * (size - 1) / float(numSeeds - 1)))
        slot = _freeSeedSlot(bracket, seededMatches, target)
        if slot is None:
            # more seeds than matches: some of them have to meet
            slot = _freeSeedSlot(bracket, set(), target)
        if slot is None:
            break
        bracket[slot] = seeds[seedRank - 1]
        seededMatches.add(matchOf(slot))
        slotOfSeed[seedRank] = slot

    # Byes go one to a match, to the partners of the strongest seeds first —
    # byeSlots()'s free-passage-to-the-top rule — but keyed on where the seeds
    # actually landed rather than on the standard order they were displaced
    # from, which used to hand a bye to an unseeded entrant.
    byeMatches = [matchOf(slotOfSeed[r]) for r in sorted(slotOfSeed)]
    byeMatches += [m for m in range(size // 2) if m not in seededMatches]
    reserved = set()
    for m in byeMatches[:byes]:
        reserved.add(2 * m if bracket[2 * m] is None else 2 * m + 1)

    for slot in _freeSlots(bracket, reserved):
        if not pool:
            break
        bracket[slot] = pool.pop(0)
    return bracket


def _freeSeedSlot(bracket, seededMatches, target):
    """The first empty slot at or after `target` whose match holds no seed."""
    size = len(bracket)
    for step in range(size):
        slot = (target + step) % size
        if bracket[slot] is None and matchOf(slot) not in seededMatches:
            return slot
    return None


def isWellFormed(slots, real):
    """Whether a slot list is a usable bracket.

    Every real entrant must appear exactly once, and no match may be empty on
    both sides — a match with nobody in it has no winner to send onward.
    """
    if len(slots) & (len(slots) - 1) != 0 or len(slots) < 2:
        return False
    placed = [s for s in slots if s is not None]
    if len(placed) != len(real) or set(id(s) for s in placed) != set(id(a) for a in real):
        return False
    for m in range(len(slots) // 2):
        if slots[2 * m] is None and slots[2 * m + 1] is None:
            return False
    return True


def drawFromOrder(entrants):
    """Read a bracket straight off an ordered entrant list.

    This is the draw the bracket editor produces: the list is the slot list,
    with a bye entrant leaving its slot empty. A list that doesn't describe a
    usable bracket — the wrong length, or a match with two byes in it — falls
    back to the positional rule in drawManual().
    """
    real = [a for a in entrants if not isBye(a)]

    # The list's own length is the bracket size, not bracketSize(len(real)):
    # the editor lets the user pick a bracket larger than the smallest one
    # their entrants fit into (four clubs deliberately drawn as eight
    # quarter-finals, each with a bye). Sizing from the entrant count instead
    # would truncate the list here and silently re-pair the whole draw.
    # isWellFormed already rejects a length that isn't a power of two.
    slots = [None if isBye(a) else a for a in entrants]
    if isWellFormed(slots, real):
        return slots
    return drawManual(real, bracketSize(len(real)))


def draw(entrants, method, numSeeds=0, rng=None):
    """Build a first-round bracket for `entrants` using the named method."""
    size = bracketSize(len(entrants))
    if len(entrants) > size:
        raise ValueError("%d entrants do not fit a %d-slot bracket" % (len(entrants), size))

    if method == MANUAL:
        return drawManual(entrants, size)
    if method == SEEDED:
        return drawSeeded(entrants, size, rng)
    if method == VARIABLE_SEEDS:
        return drawVariableSeeds(entrants, size, numSeeds, rng)
    return drawRandom(entrants, size, rng)
