"""The Scorinate step with an event that has nobody in it."""

import pytest
from builders import LISA, SPRINT

from xkoranate.competitions.competitionfactory import XkorCompetitionFactory
from xkoranate.event import XkorEvent
from xkoranate.group import XkorGroup
from xkoranate.rplist import XkorRPList
from xkoranate.startlist import XkorStartList
from xkoranate.xml.xmlsportreader import XkorXmlSportReader


@pytest.fixture
def dialogs(monkeypatch):
    """The text of every question and message box, none of them shown:
    questions are answered OK."""
    from xkoranate.eventeditor import scorinatewidget

    shown = []

    class Box:
        def exec(self):
            return 0

    monkeypatch.setattr(scorinatewidget, "confirm",
                        lambda parent, text, *args, **kwargs: (shown.append(("ask", text)), True)[1])
    monkeypatch.setattr(scorinatewidget, "message_box",
                        lambda parent, text, *args, **kwargs: (shown.append(("tell", text)), Box())[1])
    return shown


@pytest.mark.parametrize("groups", [[], [XkorGroup("Group A", [])]], ids=["no groups", "an empty group"])
@pytest.mark.parametrize("competition", list(XkorCompetitionFactory.competitionTypes()))
@pytest.mark.parametrize("sportName", [LISA, SPRINT], ids=["head-to-head", "race"])
def test_an_event_with_nobody_in_it_has_nothing_to_scorinate(qapp, sport_index, dialogs, sportName,
                                                             competition, groups):
    """A round robin with nobody in it counted −1 matchdays, which slipped
    past the "nothing to scorinate" check: the user was asked whether to
    regenerate a round with no name, and OK stored a result for matchday −1.
    Archery, multiple-run and shooting, which have matchdays even when empty,
    raised IndexError looking for a first group."""
    from xkoranate.eventeditor.scorinatewidget import XkorScorinateWidget

    sport = XkorXmlSportReader(sport_index.lookup(sportName)).sport()
    ev = XkorEvent()
    ev.setSport(sportName, sport.paradigm())
    ev.setCompetition(competition)
    ev.setGroups(list(groups))
    w = XkorScorinateWidget()
    confirmed = []
    w.resultConfirmed.connect(lambda md, text: confirmed.append(md))
    w.setEvent(ev, XkorRPList(), sport)

    w.scorinate()

    assert dialogs == [("tell", "There is nothing to scorinate yet.")]
    assert confirmed == []
    assert w.lastMatchday == -1


def test_a_round_robin_with_nobody_in_it_has_no_matchdays(qapp):
    c = XkorCompetitionFactory.newCompetition("roundRobin")
    c.init(XkorStartList(), None, {}, {}, {})
    assert c.matchdays() == 0
    assert c.matchdayNames() == []
