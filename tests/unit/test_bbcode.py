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


def test_winners_are_bolded_whichever_dash_the_sport_file_uses():
    """esports_bestof1.xml used an ASCII hyphen, and bolding silently stopped."""
    for dash in ("-", "\u2013", "\u2014"):
        line = "Aquilla (AQU) 3%s1 Busby (BUS)" % dash
        assert boldWinnerLine(line) == "[b]Aquilla (AQU)[/b] 3%s1 Busby (BUS)" % dash
