from paradigm_helpers import make_athlete, make_paradigm, make_sport

from xkoranate.paradigms.wrestlingparadigm import XkorWrestlingParadigm, XkorWrestlingParadigmResult


def test_result_reverse_swaps_scores_and_labels():
    r = XkorWrestlingParadigmResult(homeScore=3, awayScore=1, result="pin",
                                     reversedResult="lost by pin", annotation="note")
    rev = r.reverse()
    assert rev.homeScore == 1
    assert rev.awayScore == 3
    assert rev.result == "lost by pin"
    assert rev.reversedResult == "pin"
    assert rev.annotation == "note"


def test_generateScore_selects_and_orients_result_when_home_wins_the_roll(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randWeightedH2H", lambda skill, opp: 0.9 if skill == 0.9 else 0.1)
    p = make_paradigm(XkorWrestlingParadigm,
                       opts={"winnerScores": [3], "loserScores": [0], "resultProbs": [1.0]},
                       sport=sport)

    result = p.generateScore(0.9, 0.1)

    assert result.homeScore == 3
    assert result.awayScore == 0
    assert result.result == "3–0"


def test_generateScore_reverses_result_when_away_wins_the_roll(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randWeightedH2H", lambda skill, opp: 0.1 if skill == 0.9 else 0.9)
    p = make_paradigm(XkorWrestlingParadigm,
                       opts={"winnerScores": [3], "loserScores": [0], "resultProbs": [1.0]},
                       sport=sport)

    result = p.generateScore(0.9, 0.1)

    assert result.homeScore == 0
    assert result.awayScore == 3
    assert result.result == "0–3"


def test_scorinate_builds_output_and_results_for_each_match(monkeypatch):
    sport = make_sport(seed=1)
    monkeypatch.setattr(sport, "randWeightedH2H", lambda skill, opp: 0.9 if skill == 0.9 else 0.1)
    p = make_paradigm(XkorWrestlingParadigm,
                       opts={"winnerScores": [3], "loserScores": [0], "resultProbs": [1.0]},
                       sport=sport)
    athletes = [make_athlete(name="A", rp_skill=0.9), make_athlete(name="B", rp_skill=0.1)]

    p.scorinate(athletes)

    assert len(p.res) == 2
    assert p.res[0].score() == 3
    assert p.res[1].score() == 0
    assert p.out == [("A", "A 3–0 B")]
