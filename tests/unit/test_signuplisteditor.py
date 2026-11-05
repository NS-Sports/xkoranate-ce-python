"""The participants page: the skill range and the modes it is derived in."""

import pytest
from builders import make_athletes, make_signup_list

from xkoranate.signuplist import XkorSignupList
from xkoranate.signuplisteditor.signuplisteditor import XkorSignupListEditor
from xkoranate.xml.xmlsportreader import XkorXmlSportReader

# a paradigm that rescales skill, so "Maximum skill" is an organiser-set
# ceiling ("manual" mode) rather than pinned or fixed
RESCALING_SPORT = "Golf"


def signupList(skills, maxRank):
    return make_signup_list(make_athletes(len(skills), nation="AAA", skills=skills), max_rank=maxRank)


@pytest.fixture
def editor(qapp, sport_index):
    sport = XkorXmlSportReader(sport_index.lookup(RESCALING_SPORT)).sport()
    w = XkorSignupListEditor()
    w.setSport(sport, {})
    assert w.athletes is not None
    return w


def maxRankMode(editor):
    return editor._maxRankMode()


def test_loading_keeps_a_ceiling_the_organiser_set_below_the_field(editor):
    """Loading an event used to lift a deliberately lowered ceiling.

    setMaxRank() bounds the entry spinbox but doesn't clamp skills already
    stored, so a field entered at 90 under a 100 ceiling survives being
    lowered to 50 — and every later load pushed the ceiling back up to 90,
    silently rescaling the whole field while isLoading suppressed the
    modified marker.
    """
    if maxRankMode(editor) != "manual":
        pytest.skip("%s is not an organiser-set-ceiling paradigm" % RESCALING_SPORT)
    editor.setData(signupList([90.0, 80.0, 70.0], maxRank=50.0))
    assert editor.maxRank.value() == pytest.approx(50.0)
    assert editor.data().maxRank() == pytest.approx(50.0)


def test_a_paradigm_change_still_lifts_a_ceiling_the_field_has_outgrown(editor):
    """The case the lift exists for: a pass-through paradigm pins the ceiling
    to 1.0, and switching to one that rescales must not keep it."""
    if maxRankMode(editor) != "manual":
        pytest.skip("%s is not an organiser-set-ceiling paradigm" % RESCALING_SPORT)
    editor.setData(signupList([90.0, 80.0], maxRank=1.0))
    assert editor.maxRank.value() == pytest.approx(1.0)  # left as loaded

    editor._applyMaxRankMode()  # what a genuine sport change does
    assert editor.maxRank.value() == pytest.approx(90.0)


def test_unpinning_the_ceiling_lifts_it_to_the_field(editor):
    if maxRankMode(editor) != "manual":
        pytest.skip("%s is not an organiser-set-ceiling paradigm" % RESCALING_SPORT)
    editor.setData(signupList([90.0, 80.0], maxRank=1.0))
    editor.pinMaxToParticipants.setChecked(True)
    editor.pinMaxToParticipants.setChecked(False)
    assert editor.maxRank.value() == pytest.approx(90.0)


def importFile(editor, tmp_path, skills):
    f = tmp_path / "signups.txt"
    f.write_text("".join("Team %d;T%02d;%s\n" % (i, i, skill) for i, skill in enumerate(skills)),
                 encoding="utf-8")
    editor.athletes.importAthletes(str(f))


def test_importing_into_a_new_event_lifts_the_ceiling_to_the_field(editor, tmp_path):
    """A new event's ceiling is 1, and an import used to leave it there, so a
    field ranked 0-100 was scorinated on its raw ranks (and NSFS baseball's
    odds overflowed on them)."""
    if maxRankMode(editor) != "manual":
        pytest.skip("%s is not an organiser-set-ceiling paradigm" % RESCALING_SPORT)
    editor.setData(XkorSignupList())
    assert editor.maxRank.value() == pytest.approx(1.0)

    importFile(editor, tmp_path, [91, 42])

    assert editor.maxRank.value() == pytest.approx(91.0)
    assert editor.data().adjustRank(91) == pytest.approx(1.0)


def test_importing_leaves_a_ceiling_above_the_field_alone(editor, tmp_path):
    if maxRankMode(editor) != "manual":
        pytest.skip("%s is not an organiser-set-ceiling paradigm" % RESCALING_SPORT)
    editor.setData(signupList([50.0], maxRank=100.0))

    importFile(editor, tmp_path, [91, 42])

    assert editor.maxRank.value() == pytest.approx(100.0)
