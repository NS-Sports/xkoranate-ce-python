from paradigm_helpers import make_athlete, make_paradigm, make_sport

from xkoranate.paradigms.howzzatparadigm import XkorHowzzatParadigm


def test_generateFTScore_produces_bounded_valid_result():
    sport = make_sport(seed=42, paradigm_options={"maxOvers": 50, "ballsPerOver": 6, "maxWickets": 10})
    p = make_paradigm(XkorHowzzatParadigm, sport=sport)
    home = make_athlete(name="Home", rp_skill=0.6)
    away = make_athlete(name="Away", rp_skill=0.4)

    hRes, aRes = p.generateFTScore(home, away)

    assert hRes.score() >= 0
    assert aRes.score() >= 0
    assert 0 <= hRes.value("wickets") <= 10
    assert 0 <= aRes.value("wickets") <= 10
    assert 0 <= hRes.value("balls") <= 300
    assert 0 <= aRes.value("balls") <= 300


def test_generateFTScore_caps_second_batting_teams_winning_margin(monkeypatch):
    sport = make_sport(seed=1)
    # exact RNG call order in generateFTScore: 10 interleaved randUniform()
    # calls picking style/batting-order/rate-modifier branches, then 4
    # randGaussian() calls for the run/wicket rates, then a final
    # randUniform() for winningRuns
    uniforms = iter([0.9, 0.1, 0.05, 0.9, 0.95, 0.1, 0.5, 0.9, 0.5, 0.9, 0.0])
    monkeypatch.setattr(sport, "randUniform", lambda: next(uniforms))
    monkeypatch.setattr(sport, "randGaussian", lambda: 0.0)
    p = make_paradigm(XkorHowzzatParadigm, opts={"maxOvers": 50, "ballsPerOver": 6, "maxWickets": 10}, sport=sport)
    home = make_athlete(name="Home", rp_skill=0.5)
    away = make_athlete(name="Away", rp_skill=0.5)

    hRes, aRes = p.generateFTScore(home, away)

    # home batted first and would otherwise have lost by a huge margin
    # (raw away total ~360 vs home's 176); the "couldn't have won by more
    # than winningRuns" rule caps it to homeRuns + winningRuns instead
    assert hRes.score() == 176.0
    assert aRes.score() == 177.0
    assert hRes.value("wickets") == 6.0
    assert aRes.value("wickets") == 5.0
    assert hRes.value("balls") == 300
    assert aRes.value("balls") == 147
