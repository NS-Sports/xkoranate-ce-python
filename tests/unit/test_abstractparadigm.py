from paradigm_helpers import make_athlete

from xkoranate.paradigms.abstractparadigm import XkorAbstractParadigm
from xkoranate.result import XkorResult


def test_compare_ascending_by_default():
    p = XkorAbstractParadigm()
    low = XkorResult(score=1.0)
    high = XkorResult(score=2.0)
    assert p.compare(low, high) == -1
    assert p.compare(high, low) == 1
    assert p.compare(low, low) == 0


def test_compare_descending_when_configured():
    p = XkorAbstractParadigm()
    p.opt = {"sortOrder": "descending"}
    low = XkorResult(score=1.0)
    high = XkorResult(score=2.0)
    assert p.compare(low, high) == 1
    assert p.compare(high, low) == -1


def test_outputLine_formats_name_with_nation_and_padded_score():
    p = XkorAbstractParadigm()
    r = XkorResult(score=42.0, ath=make_athlete(name="Alice", nation="USA"))
    assert p.outputLine(r) == "Alice (USA)".ljust(22) + "42".rjust(12)


def test_outputLine_omits_nation_when_showTLAs_is_false():
    p = XkorAbstractParadigm()
    p.userOpt = {"showTLAs": "false"}
    r = XkorResult(score=1.0, ath=make_athlete(name="Alice", nation="USA"))
    assert p.outputLine(r) == "Alice".ljust(22) + "1".rjust(12)


def test_readOptionList_wraps_scalar_value_in_a_list():
    p = XkorAbstractParadigm()
    p.opt = {"foo": "bar"}
    assert p.readOptionList("foo") == ["bar"]


def test_readOptionList_passes_through_list_values():
    p = XkorAbstractParadigm()
    p.opt = {"foo": [1, 2, 3]}
    assert p.readOptionList("foo") == [1, 2, 3]


def test_readOptionList_returns_empty_list_for_missing_key():
    p = XkorAbstractParadigm()
    p.opt = {}
    assert p.readOptionList("missing") == []


def test_timeFormat_seconds_only():
    p = XkorAbstractParadigm()
    assert p.timeFormat(45.26, 1) == "45.3"


def test_timeFormat_minutes_and_seconds_with_leading_zero():
    p = XkorAbstractParadigm()
    assert p.timeFormat(65.5, 2) == "1:05.50"


def test_timeFormat_hours_minutes_and_seconds():
    p = XkorAbstractParadigm()
    assert p.timeFormat(3725.4, 0) == "1:02:05"


def test_addResults_clones_and_applies_outputLine():
    p = XkorAbstractParadigm()
    original = XkorResult(score=10.0, ath=make_athlete(name="Bob"))

    p.addResults([original])

    assert len(p.results()) == 1
    cloned = p.results()[0]
    assert cloned is not original
    assert cloned.score() == 10.0
    assert cloned.output() == p.outputLine(original)


def test_output_joins_out_entries_with_newlines():
    p = XkorAbstractParadigm()
    p.out = [("A", "line one"), ("B", "line two")]
    assert p.output() == "line one\nline two\n"
