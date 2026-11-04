from xkoranate.competitions.roundrobincompetition import XkorRoundRobinCompetition

# what scorinateMatchday saves: “matchday: Home score–score [OT|SO] Away”.
# Taekwondo deducts penalty points, so a score can be below zero.
SAVED = [
    "0: Aquilla 3–1 Busby",
    "0: Corvina 6–-1 Delmar",
    "1: Aquilla -2–0 OT Corvina",
    "2: Busby -1–-2 Delmar",
]


def competition(saved):
    c = XkorRoundRobinCompetition()
    c.userOpt = {"tableData": [list(saved)]}
    return c


def test_negative_scores_are_read_back_into_the_table():
    matches = competition(SAVED).retrieveMatches(0)
    assert [(m.team1, m.score1, m.score2, m.team2) for m in matches] == [
        ("Aquilla", 3, 1, "Busby"),
        ("Corvina", 6, -1, "Delmar"),
        ("Aquilla", -2, 0, "Corvina"),
        ("Busby", -1, -2, "Delmar"),
    ]
    assert matches[2].decider == "OT"


def test_reverting_drops_later_negative_scores_too():
    resume = competition(SAVED).revertToMatchday(1)
    assert resume["tableData"] == [SAVED[:2]]
