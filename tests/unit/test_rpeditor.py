"""The bonuses page: loading a bonus list shows it as it is, and asks nothing."""

import pytest

from xkoranate.rpeditor import rpeditor
from xkoranate.rplist import XkorRPList


def bonusList(formula, bonuses=None, teams=True):
    rpl = XkorRPList()
    rpl.setRPCalculationType(formula)
    rpl.setBonuses({code: {"bonus": value} for code, value in (bonuses or {}).items()})
    rpl.setUseTeams(teams)
    return rpl


@pytest.fixture
def asked(monkeypatch):
    """Every "reset all bonuses?" question, each answered Cancel."""
    questions = []
    monkeypatch.setattr(rpeditor, "confirm",
                        lambda parent, text, *args, **kwargs: (questions.append(text), False)[1])
    return questions


def test_loading_a_bonus_list_asks_nothing_and_shows_its_formula(qapp, asked):
    """The formula dropdown follows the list being loaded, and that used to
    count as the user changing it: with the last file's bonuses still on
    screen it asked to reset them, and Cancel left the old formula showing
    and then wrote it into the list just loaded."""
    editor = rpeditor.XkorRPEditor()
    editor.setData(bonusList("olympic", {"AAA": 5.0}))

    loaded = bonusList("wc36")
    editor.setData(loaded)

    assert asked == []
    assert editor.m_rpCalcType.currentData() == "wc36"
    assert editor.m_currentRPCalcType == "wc36"
    editor.updateData()
    assert loaded.rpCalculationType() == "wc36"


def test_loading_takes_team_or_participant_bonuses_from_the_new_list(qapp, asked):
    """The bonus widget rebuilt for the new list's formula is headed from
    that list's choice, not the one being replaced."""
    editor = rpeditor.XkorRPEditor()
    editor.setData(bonusList("olympic", teams=True))

    editor.setData(bonusList("wc36", teams=False))

    header = editor.m_rpBonus.treeWidget.headerItem().text(0)
    assert header == "Participant"


def test_changing_the_formula_by_hand_still_asks(qapp, asked):
    rpl = bonusList("olympic", {"AAA": 5.0})
    editor = rpeditor.XkorRPEditor()
    editor.setData(rpl)

    editor.m_rpCalcType.setCurrentIndex(editor.m_rpCalcType.findData("wc36"))

    assert len(asked) == 1
    assert editor.m_rpCalcType.currentData() == "olympic"  # Cancel put it back
    assert editor.m_rpBonus.bonuses() == {"AAA": {"bonus": 5.0}}
