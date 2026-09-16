"""QVariant-style coercion helpers.

The C++ code stores options as QVariant and converts with toDouble()/toInt()/
toBool()/etc. Values parsed from XML are strings; values set by widgets may be
int/float/bool/list. These helpers reproduce Qt's conversion semantics.
"""

import uuid


def qNumber(v):
    """QString::number(double): 'g' format, 6 significant digits."""
    s = "%.6g" % v
    # Qt writes exponents as e+05 too; %g already matches closely enough
    return s


def toString(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return qNumber(v)
    if isinstance(v, uuid.UUID):
        return "{%s}" % v
    return str(v)


def _normaliseSeparators(s):
    """Accept both decimal points and decimal commas.

    Spreadsheets in comma-decimal locales paste numbers as ‘30,06’, and files
    written that way have to keep loading. A dot always wins as the decimal
    separator, so any comma alongside one is a thousands separator; a lone
    comma is the decimal separator; several commas are thousands separators.
    """
    s = s.strip()
    if "." in s:
        return s.replace(",", "")
    if s.count(",") > 1:
        return s.replace(",", "")
    return s.replace(",", ".")


def toDouble(v):
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(_normaliseSeparators(str(v)))
    except (TypeError, ValueError):
        return 0.0


def toInt(v):
    if v is None:
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return round(v)  # Qt rounds doubles on toInt
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        try:
            return round(float(_normaliseSeparators(str(v))))
        except (TypeError, ValueError):
            return 0


def toUInt(v):
    n = toInt(v)
    return n if n >= 0 else 0


def toBool(v):
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v)
    return not (s == "" or s == "0" or s.lower() == "false")


def toList(v):
    if isinstance(v, list):
        return list(v)
    if isinstance(v, tuple):
        return list(v)
    return []  # Qt: non-list QVariant converts to empty list


def toStringList(v):
    if isinstance(v, (list, tuple)):
        return [toString(x) for x in v]
    if isinstance(v, str) and v != "":
        return [v]
    return []
