"""Backwards compatibility of the reader with hand-edited 0.3 files.

Files in the wild are not always the pretty-printed output of our own writer:
spreadsheets and scripts paste signups in with the indentation stripped, and
comma-decimal locales write ‘30,06’ where we write ‘30.06’. Those files loaded
in earlier editions, so they have to keep loading.
"""

import re
import pytest

from xkoranate.xml.xmlreader import XkorXmlReader

PRETTY = """<?xml version="1.0" encoding="UTF-8"?>
<scorinationFile version="0.3">
    <rpList>
        <useTeams>true</useTeams>
        <competitionName>Test Cup</competitionName>
        <rpEffect>0.25</rpEffect>
        <rpCalculationType>linear</rpCalculationType>
        <minBonus>-1.5</minBonus>
        <maxBonus>1.5</maxBonus>
        <rpOptions>
            <double type="weight">0.75</double>
        </rpOptions>
        <nation name="AAA">
            <property type="bonus">0.5</property>
        </nation>
    </rpList>
    <event id="{11111111-1111-1111-1111-111111111111}" name="Test Event">
        <sport>Association football</sport>
        <competition>roundRobin</competition>
        <paradigmOptions>
            <double type="homeAdvantage">0.1</double>
            <int type="matchdays">3</int>
        </paradigmOptions>
        <competitionOptions>
            <string type="seeding">skill</string>
        </competitionOptions>
        <results>
            <result matchday="1">1-0</result>
        </results>
        <signupList>
            <minRank>0</minRank>
            <maxRank>100</maxRank>
            <signup id="{23f10264-40ce-8cff-aea8-f6623b14a971}" name="Aubury Swans" nation="" skill="30.06">
                <string type="style">-0.5</string>
            </signup>
            <signup id="{23f10264-40ce-8cff-aea8-f6623b14a972}" name="Beeton Bears" nation="BBB" skill="28.5">
                <string type="style">0.25</string>
            </signup>
            <signup id="{23f10264-40ce-8cff-aea8-f6623b14a973}" name="Ceedham City" nation="CCC" skill="12.125">
                <string type="style">1.5</string>
            </signup>
        </signupList>
        <group name="Group A">
            <signup>{23f10264-40ce-8cff-aea8-f6623b14a971}</signup>
            <signup>{23f10264-40ce-8cff-aea8-f6623b14a972}</signup>
            <signup>{23f10264-40ce-8cff-aea8-f6623b14a973}</signup>
        </group>
    </event>
</scorinationFile>
"""

def _compact(text):
    """Strip the indentation between elements, as a spreadsheet paste does."""
    return re.sub(r">\s+<", "><", text).strip()


def _commas(text):
    """Rewrite every decimal separator as a comma, as a comma-decimal locale does.

    The XML declaration and the file's own version attribute are format, not
    data, so they keep their dots.
    """
    header, _, body = text.partition("<rpList>")
    return header + "<rpList>" + re.sub(r"(?<=\d)\.(?=\d)", ",", body)


VARIANTS = {
    "pretty": PRETTY,                       # what our own writer produces
    "compact": _compact(PRETTY),            # issue #56
    "commas": _commas(PRETTY),              # issue #57
    "compact_commas": _compact(_commas(PRETTY)),  # both, as users actually hit it
}

SIGNUPS = [
    ("23f10264-40ce-8cff-aea8-f6623b14a971", "Aubury Swans", "", 30.06, "-0.5"),
    ("23f10264-40ce-8cff-aea8-f6623b14a972", "Beeton Bears", "BBB", 28.5, "0.25"),
    ("23f10264-40ce-8cff-aea8-f6623b14a973", "Ceedham City", "CCC", 12.125, "1.5"),
]


def _read(tmp_path, text, name):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    reader = XkorXmlReader(str(path))
    assert reader.error() == ""
    return reader


def _styles(athlete):
    # The style mod is stored as a string; only the comma variants change it.
    return athlete.properties["style"]


@pytest.mark.parametrize("name", list(VARIANTS))
def test_signups_survive_whitespace_and_separator_variations(tmp_path, name):
    reader = _read(tmp_path, VARIANTS[name], name + ".xkor")
    events = reader.events()
    assert len(events) == 1
    event = events[0][1]

    athletes = event.signupList().athletes()
    assert [a.name for a in athletes] == [s[1] for s in SIGNUPS]
    assert [str(a.id) for a in athletes] == [s[0] for s in SIGNUPS]
    assert [a.nation for a in athletes] == [s[2] for s in SIGNUPS]
    assert [a.skill for a in athletes] == pytest.approx([s[3] for s in SIGNUPS])

    # Groups resolve against the signup list, so a dropped signup surfaces here
    # as an ‘unknown participant’ rather than as a missing row.
    group = event.groups()[0]
    assert [str(i) for i in group.athletes] == [s[0] for s in SIGNUPS]
    known = {a.id for a in athletes}
    assert all(i in known for i in group.athletes)


@pytest.mark.parametrize("name", list(VARIANTS))
def test_rest_of_the_file_survives_too(tmp_path, name):
    reader = _read(tmp_path, VARIANTS[name], name + ".xkor")
    event = reader.events()[0][1]

    assert event.name() == "Test Event"
    assert event.sport() == "Association football"
    assert event.competition() == "roundRobin"
    assert event.paradigmOptions()["homeAdvantage"] == pytest.approx(0.1)
    assert event.paradigmOptions()["matchdays"] == 3
    assert event.competitionOptions()["seeding"] == "skill"
    assert event.results()[1] == "1-0"
    assert event.signupList().minRank() == pytest.approx(0)
    assert event.signupList().maxRank() == pytest.approx(100)

    rpList = reader.rpList()
    assert rpList.competitionName() == "Test Cup"
    assert rpList.useTeams() is True
    assert rpList.rpEffect() == pytest.approx(0.25)
    assert rpList.minBonus() == pytest.approx(-1.5)
    assert rpList.maxBonus() == pytest.approx(1.5)
    assert rpList.rpOptions()["weight"] == pytest.approx(0.75)
    assert rpList.bonuses()["AAA"]["bonus"] == pytest.approx(0.5)


def test_style_mods_parse_as_numbers_with_either_separator(tmp_path):
    from xkoranate.variant import toDouble

    pretty = _read(tmp_path, VARIANTS["pretty"], "p.xkor").events()[0][1]
    commas = _read(tmp_path, VARIANTS["commas"], "c.xkor").events()[0][1]

    expected = [-0.5, 0.25, 1.5]
    for athletes in (pretty.signupList().athletes(), commas.signupList().athletes()):
        assert [toDouble(_styles(a)) for a in athletes] == pytest.approx(expected)
