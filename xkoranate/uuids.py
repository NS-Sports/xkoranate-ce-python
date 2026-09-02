"""Conversions between uuids and the braced strings the file format uses.

These were copied into seven modules, in two variants that look alike but
aren't: the editors treat a null uuid as "nothing assigned yet" and hand back
None, while the readers keep it as a value in its own right. Both are needed,
so both are here under names that say which is which.
"""

import uuid

NULL_UUID_STRING = "{00000000-0000-0000-0000-000000000000}"


def uuidToString(u):
    """QUuid::toString(): the braced form, with None rendering as null."""
    if u is None:
        return NULL_UUID_STRING
    return "{%s}" % u


def parseUuid(s):
    """QUuid(QString): the uuid s names, or None if it doesn't name one.

    A null uuid is a value here, not an absence — it parses to UUID(int=0).
    Use parseAssignedUuid() where a null uuid means "nothing chosen".
    """
    try:
        return uuid.UUID(str(s).strip("{}"))
    except (AttributeError, TypeError, ValueError):
        return None


def parseAssignedUuid(s):
    """The uuid s names, or None if it names nothing.

    Unparseable and null both come back as None: an editor row that hasn't
    been given a participant yet carries a null uuid, and callers want to
    treat that the same as an empty one.
    """
    rval = parseUuid(s)
    return None if rval is None or rval.int == 0 else rval
