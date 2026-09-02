"""The two uuid-parsing behaviours the app relies on, which used to be
copied into seven modules under names that didn't distinguish them."""

import uuid

import pytest

from xkoranate.uuids import NULL_UUID_STRING, parseAssignedUuid, parseUuid, uuidToString

SOME_UUID = uuid.UUID("3f2a1c9e-4b6d-4a71-9c2e-8d5f0a1b2c3d")


def test_uuid_to_string_uses_the_braced_form():
    assert uuidToString(SOME_UUID) == "{3f2a1c9e-4b6d-4a71-9c2e-8d5f0a1b2c3d}"


def test_none_renders_as_the_null_uuid():
    assert uuidToString(None) == NULL_UUID_STRING


def test_a_uuid_survives_a_round_trip():
    assert parseUuid(uuidToString(SOME_UUID)) == SOME_UUID
    assert parseAssignedUuid(uuidToString(SOME_UUID)) == SOME_UUID


def test_parse_uuid_keeps_a_null_uuid_as_a_value():
    """The file format writes null uuids, and the readers round-trip them."""
    assert parseUuid(NULL_UUID_STRING) == uuid.UUID(int=0)


def test_parse_assigned_uuid_treats_a_null_uuid_as_nothing():
    """An editor row with no participant chosen carries a null uuid."""
    assert parseAssignedUuid(NULL_UUID_STRING) is None


@pytest.mark.parametrize("value", ["", "not-a-uuid", None, 42, object()])
def test_neither_parser_raises_on_junk(value):
    assert parseUuid(value) is None
    assert parseAssignedUuid(value) is None


def test_unbraced_input_is_accepted_too():
    assert parseUuid(str(SOME_UUID)) == SOME_UUID
