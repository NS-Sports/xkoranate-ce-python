import uuid

import pytest

from xkoranate.variant import (
    qNumber,
    toBool,
    toDouble,
    toInt,
    toList,
    toString,
    toStringList,
    toUInt,
)


def test_qNumber_uses_six_significant_digits():
    assert qNumber(1.0) == "1"
    assert qNumber(0.123456789) == "0.123457"
    assert qNumber(1234567.0) == "1.23457e+06"


@pytest.mark.parametrize("value,expected", [
    (None, ""),
    (True, "true"),
    (False, "false"),
    (1.5, "1.5"),
    ("already a string", "already a string"),
    (42, "42"),
])
def test_toString(value, expected):
    assert toString(value) == expected


def test_toString_formats_uuid_with_braces():
    u = uuid.UUID(int=1)
    assert toString(u) == "{%s}" % u


@pytest.mark.parametrize("value,expected", [
    (None, 0.0),
    (True, 1.0),
    (False, 0.0),
    (3, 3.0),
    (3.5, 3.5),
    ("2.5", 2.5),
    ("not a number", 0.0),
    # Comma-decimal locales paste numbers in this way; earlier editions read
    # them, so they still have to parse.
    ("2,5", 2.5),
    ("30,06", 30.06),
    ("-0,5", -0.5),
    (" 1,5 ", 1.5),
    # A dot wins as the decimal separator, so commas beside it group thousands.
    ("1,234", 1.234),
    ("1,234.5", 1234.5),
    ("1,234,567", 1234567.0),
])
def test_toDouble(value, expected):
    assert toDouble(value) == expected


@pytest.mark.parametrize("value,expected", [
    (None, 0),
    (True, 1),
    (False, 0),
    (5, 5),
    (5.6, 6),
    (5.4, 5),
    ("7", 7),
    ("7.6", 8),
    ("7,6", 8),
    # A lone comma is the decimal separator, never a thousands separator:
    # ‘1,234’ is one and a bit, which rounds down.
    ("1,234", 1),
    ("not a number", 0),
])
def test_toInt(value, expected):
    assert toInt(value) == expected


@pytest.mark.parametrize("value,expected", [
    (5, 5),
    (-5, 0),
    ("-3", 0),
    ("4", 4),
])
def test_toUInt(value, expected):
    assert toUInt(value) == expected


@pytest.mark.parametrize("value,expected", [
    (None, False),
    (True, True),
    (False, False),
    (0, False),
    (1, True),
    ("", False),
    ("0", False),
    ("false", False),
    ("False", False),
    ("anything else", True),
])
def test_toBool(value, expected):
    assert toBool(value) == expected


def test_toList_passes_through_lists_and_tuples():
    assert toList([1, 2, 3]) == [1, 2, 3]
    assert toList((1, 2, 3)) == [1, 2, 3]


def test_toList_returns_empty_for_non_sequence():
    assert toList("abc") == []
    assert toList(None) == []


def test_toStringList():
    assert toStringList([1, True, "x"]) == ["1", "true", "x"]
    assert toStringList("solo") == ["solo"]
    assert toStringList("") == []
    assert toStringList(None) == []
