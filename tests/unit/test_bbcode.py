from xkoranate.bbcode import boldWinnerLine, boldWinners


def test_boldWinnerLine_bolds_home_winner_in_score_line():
    assert boldWinnerLine("Home 3–1 Away") == "[b]Home[/b] 3–1 Away"


def test_boldWinnerLine_bolds_away_winner_in_score_line():
    assert boldWinnerLine("Away 1–3 Home") == "Away 1–3 [b]Home[/b]"


def test_boldWinnerLine_leaves_draw_unchanged():
    assert boldWinnerLine("Team A 2–2 Team B") == "Team A 2–2 Team B"


def test_boldWinnerLine_bolds_winner_in_def_wording():
    assert boldWinnerLine("Alice def. Bob (retired)") == "[b]Alice[/b] def. Bob (retired)"


def test_boldWinnerLine_bolds_winner_in_def_by_wording():
    assert boldWinnerLine("Alice def. by Bob (injury)") == "Alice def. by [b]Bob[/b] (injury)"


def test_boldWinnerLine_preserves_trailing_tiebreak_note():
    assert (boldWinnerLine("Home 3–1 Away (5–3 penalties)")
            == "[b]Home[/b] 3–1 Away (5–3 penalties)")
    assert (boldWinnerLine("Away 1–3 Home (5–3 penalties)")
            == "Away 1–3 [b]Home[/b] (5–3 penalties)")


def test_boldWinnerLine_leaves_unrecognised_lines_unchanged():
    assert boldWinnerLine("Group A") == "Group A"


def test_boldWinnerLine_leaves_padded_table_rows_unchanged():
    # standings table rows (position/name/columns padded with ljust/rjust)
    # can coincidentally contain "3–1"-style results-grid cells; these must
    # not be mistaken for a "Name score–score Name" match line, since real
    # match lines are single-space-joined with no column padding
    row = " 1 Athlete 1      1   1   0   0    3    1   +2    3                        —    —    —   3–1"
    assert boldWinnerLine(row) == row


def test_boldWinners_processes_each_line_independently():
    text = "Group A\nHome 3–1 Away\nHome2 0–0 Away2"
    assert boldWinners(text) == "Group A\n[b]Home[/b] 3–1 Away\nHome2 0–0 Away2"


def test_winners_are_bolded_for_the_dashes_sport_files_use():
    """esports_bestof1.xml used an ASCII hyphen and bolding silently stopped;
    the file was corrected to an en dash, which is what every other sport file
    uses. The hyphen is deliberately not accepted here — it is a Gaelic
    score's goals-points separator, and matching it corrupted those lines."""
    for dash in ("\u2013", "\u2014"):
        line = "Aquilla (AQU) 3%s1 Busby (BUS)" % dash
        assert boldWinnerLine(line) == "[b]Aquilla (AQU)[/b] 3%s1 Busby (BUS)" % dash

    hyphenated = "Aquilla (AQU) 3-1 Busby (BUS)"
    assert boldWinnerLine(hyphenated) == hyphenated


def test_boldWinnerLine_leaves_gaelic_scores_unchanged():
    """Accepting an ASCII hyphen let _SCORE_LINE_RE read a Gaelic goals-points
    separator as a home-away divider, bolding a nonsense span."""
    for line in ("Kerry 1-12 (15) def. Dublin 0-14 (14)",
                 "Dublin 0-14 (14) def. by Kerry 1-12 (15)"):
        assert boldWinnerLine(line) == line


def test_boldWinnerLine_leaves_a_drawn_gaelic_match_unchanged():
    """The worst of the hyphen regression: a draw was given a bolded winner."""
    line = "Cork 2-08 (14) drew with Mayo 1-11 (14)"
    assert boldWinnerLine(line) == line


def test_boldWinnerLine_leaves_australian_scores_unchanged():
    line = "Geelong 12.8 (80) def. Carlton 10.5 (65)"
    assert boldWinnerLine(line) == line
