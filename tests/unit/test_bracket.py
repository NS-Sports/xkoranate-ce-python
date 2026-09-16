import pytest

from xkoranate.athlete import XkorAthlete
from xkoranate.competitions import bracket
from xkoranate.rng import Mt19937


def entrants(n):
    """n athletes, strongest first (skill descending)."""
    rval = []
    for i in range(n):
        a = XkorAthlete()
        a.name = "Seed %d" % (i + 1)
        a.skill = 1.0 - i / 100.0
        rval.append(a)
    return rval


def assertWellFormed(slots, ents):
    """Every entrant placed once, and no match left with two empty slots."""
    filled = [s for s in slots if s is not None]
    assert sorted(a.name for a in filled) == sorted(a.name for a in ents)
    assert len(slots) == bracket.bracketSize(len(ents))
    for m in range(len(slots) // 2):
        assert not (slots[2 * m] is None and slots[2 * m + 1] is None)


def matchOfName(slots, name):
    for i, s in enumerate(slots):
        if s is not None and s.name == name:
            return bracket.matchOf(i)
    raise AssertionError("%s not in the bracket" % name)


def test_bracket_size_rounds_up_to_a_power_of_two():
    assert bracket.bracketSize(1) == 2
    assert bracket.bracketSize(2) == 2
    assert bracket.bracketSize(3) == 4
    assert bracket.bracketSize(8) == 8
    assert bracket.bracketSize(12) == 16
    assert bracket.bracketSize(33) == 64


def test_standard_seed_order_matches_the_reference_implementation():
    # 1 v 8, 4 v 5, 2 v 7, 3 v 6 — so seeds 1 and 2 meet only in the final
    assert bracket.standardSeedOrder(2) == [1, 2]
    assert bracket.standardSeedOrder(4) == [1, 4, 2, 3]
    assert bracket.standardSeedOrder(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_standard_seed_order_pairs_every_match_to_the_same_total():
    order = bracket.standardSeedOrder(16)
    assert sorted(order) == list(range(1, 17))
    for m in range(8):
        assert order[2 * m] + order[2 * m + 1] == 17


def test_bye_slots_face_the_strongest_seeds():
    order = bracket.standardSeedOrder(16)
    byes = bracket.byeSlots(16, 4, order)
    # the four byes are the partners of seeds 1 through 4
    assert sorted(order[bracket.partnerOf(s)] for s in byes) == [1, 2, 3, 4]


def test_bye_slots_never_share_a_match():
    order = bracket.standardSeedOrder(16)
    for count in range(1, 9):
        byes = bracket.byeSlots(16, count, order)
        assert len(byes) == count
        assert len(set(bracket.matchOf(s) for s in byes)) == count


def test_unseeded_bye_slots_also_never_share_a_match():
    byes = bracket.byeSlots(16, 5, rng=Mt19937(2026))
    assert len(byes) == 5
    assert len(set(bracket.matchOf(s) for s in byes)) == 5


def test_bye_slots_rejects_more_byes_than_matches():
    with pytest.raises(ValueError):
        bracket.byeSlots(8, 5, bracket.standardSeedOrder(8))


# the four draws the bracket editor's buttons call, behind one signature
DRAWS = {
    "manual": lambda ents, size, rng: bracket.drawManual(ents, size),
    "random": lambda ents, size, rng: bracket.drawRandom(ents, size, rng),
    "seeded": lambda ents, size, rng: bracket.drawSeeded(ents, size, rng),
    "variableSeeds": lambda ents, size, rng: bracket.drawVariableSeeds(ents, size, 4, rng),
}


@pytest.mark.parametrize("method", sorted(DRAWS))
@pytest.mark.parametrize("n", [2, 3, 5, 8, 11, 12, 16, 17])
def test_every_method_produces_a_well_formed_bracket(method, n):
    ents = entrants(n)
    slots = DRAWS[method](ents, bracket.bracketSize(n), Mt19937(2026))
    assertWellFormed(slots, ents)


@pytest.mark.parametrize("method", sorted(DRAWS))
def test_draws_are_reproducible_under_a_fixed_seed(method):
    ents = entrants(12)
    size = bracket.bracketSize(12)
    a = DRAWS[method](ents, size, Mt19937(2026))
    b = DRAWS[method](ents, size, Mt19937(2026))
    assert [x.name if x else None for x in a] == [x.name if x else None for x in b]


def test_seeded_draw_keeps_the_top_two_apart_until_the_final():
    slots = bracket.drawSeeded(entrants(16), 16)
    half = len(slots) // 2
    top = [i for i, s in enumerate(slots) if s.name == "Seed 1"][0]
    second = [i for i, s in enumerate(slots) if s.name == "Seed 2"][0]
    assert (top < half) != (second < half)


def test_seeded_draw_pairs_the_top_seed_with_the_bottom_one():
    slots = bracket.drawSeeded(entrants(8), 8)
    assert slots[0].name == "Seed 1"
    assert slots[1].name == "Seed 8"


def test_seeded_draw_gives_the_byes_to_the_top_seeds():
    slots = bracket.drawSeeded(entrants(12), 16)
    byeHolders = set()
    for m in range(8):
        home, away = slots[2 * m], slots[2 * m + 1]
        if home is None:
            byeHolders.add(away.name)
        elif away is None:
            byeHolders.add(home.name)
    assert byeHolders == {"Seed 1", "Seed 2", "Seed 3", "Seed 4"}


def test_manual_draw_uses_no_randomness():
    ents = entrants(12)
    assert bracket.drawManual(ents, 16) == bracket.drawManual(ents, 16)


def test_manual_draw_follows_list_order():
    slots = bracket.drawManual(entrants(8), 8)
    assert [s.name for s in slots] == ["Seed %d" % (i + 1) for i in range(8)]


def test_manual_draw_gives_the_byes_to_the_head_of_the_list():
    slots = bracket.drawManual(entrants(12), 16)
    # first four matches are the byes, in list order
    for m in range(4):
        assert slots[2 * m].name == "Seed %d" % (m + 1)
        assert slots[2 * m + 1] is None
    # the rest pair off two at a time
    assert slots[8].name == "Seed 5"
    assert slots[9].name == "Seed 6"


def test_manual_draw_follows_a_reordered_list():
    ents = entrants(8)
    ents.reverse()
    slots = bracket.drawManual(ents, 8)
    assert [s.name for s in slots] == [a.name for a in ents]


def test_variable_seeds_places_every_seed():
    ents = entrants(16)
    slots = bracket.drawVariableSeeds(ents, 16, 4, Mt19937(2026))
    assertWellFormed(slots, ents)
    for i in range(4):
        matchOfName(slots, "Seed %d" % (i + 1))  # raises if unplaced


def test_variable_seeds_spreads_the_seeds_into_different_matches():
    slots = bracket.drawVariableSeeds(entrants(16), 16, 4, Mt19937(2026))
    matches = [matchOfName(slots, "Seed %d" % (i + 1)) for i in range(4)]
    assert len(set(matches)) == 4


def test_variable_seeds_falls_back_to_a_random_draw_for_one_seed():
    ents = entrants(8)
    slots = bracket.drawVariableSeeds(ents, 8, 1, Mt19937(2026))
    assertWellFormed(slots, ents)


def test_variable_seeds_clamps_to_the_entrant_count():
    ents = entrants(6)
    slots = bracket.drawVariableSeeds(ents, 8, 99, Mt19937(2026))
    assertWellFormed(slots, ents)


def _seedPairings(size, n, numSeeds, rng=None):
    """First-round matches, as (seedIndex or None, seedIndex or None) pairs."""
    athletes = entrants(n)
    ranked = sorted(athletes, key=lambda a: -a.skill)
    rank = {id(a): i for i, a in enumerate(ranked)}
    slots = bracket.drawVariableSeeds(athletes, size, numSeeds, rng)
    out = []
    for m in range(size // 2):
        pair = []
        for slot in (2 * m, 2 * m + 1):
            a = slots[slot]
            pair.append(None if a is None else rank[id(a)])
        out.append(tuple(pair))
    return out


def test_variable_seeds_never_pair_two_seeds_in_the_first_round():
    """The button promises the top seeds are kept apart; byes used to break it.

    Bye slots were reserved from the standard seed order but the seeds were
    then placed at evenly spaced targets, and a seed displaced off a reserved
    slot only checked that the slot was free — not that its partner was
    already a seed. 6 entrants / 8 slots / 4 seeds put S2 against S3.
    """
    size = 2
    while size <= 64:
        for n in range(2, size + 1):
            if size - n > size // 2:
                continue
            for numSeeds in range(2, n + 1):
                if numSeeds > size // 2:
                    continue  # more seeds than matches: they must meet
                for pair in _seedPairings(size, n, numSeeds):
                    seeded = [p for p in pair if p is not None and p < numSeeds]
                    assert len(seeded) <= 1, (
                        "size=%d entrants=%d numSeeds=%d pair=%s"
                        % (size, n, numSeeds, pair))
        size *= 2


def test_variable_seeds_give_the_byes_to_the_seeds():
    """A bye handed to an unseeded entrant while a seed played was the other
    half of the same bug: 6 entrants / 8 slots / 4 seeds gave one to S6."""
    for size, n, numSeeds in ((8, 6, 4), (16, 12, 4), (16, 9, 8), (32, 20, 8)):
        pairings = _seedPairings(size, n, numSeeds)
        byeGetters = sorted(p[0] if p[1] is None else p[1]
                            for p in pairings if None in p)
        byes = size - n
        assert len(byeGetters) == byes
        # the byes went to the strongest entrants there were byes for
        assert byeGetters == list(range(byes))


def test_variable_seeds_never_leave_a_match_empty():
    for size, n, numSeeds in ((8, 4, 4), (8, 6, 2), (16, 8, 4), (32, 17, 8)):
        pairings = _seedPairings(size, n, numSeeds)
        assert all(pair != (None, None) for pair in pairings)
