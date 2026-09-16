import copy
import uuid

from .variant import toDouble, toString


# A knockout bye: a reserved id standing in for "no opponent". It is written
# into a group's entrant list like a real participant, so a bracket draw can
# hold byes in particular slots, and is stripped out again for every
# competition type that doesn't understand them (see
# XkorAbstractCompetition.acceptsByes).
# deliberately not the null uuid: a null id already means "no participant
# chosen yet" for a freshly inserted row in the event setup editor
BYE_ID = uuid.UUID("00000000-0000-0000-0000-0000000000b1")
BYE_NAME = "BYE"


def makeBye():
    """A placeholder entrant representing a bye."""
    rval = XkorAthlete(BYE_ID)
    rval.name = BYE_NAME
    return rval


def isBye(athlete):
    return athlete is not None and athlete.id == BYE_ID


class XkorAthlete:
    def __init__(self, newID=None):
        self.name = ""
        self.rpBonus = 0.0
        self.rpSkill = 0.0  # modified skill after RP bonus is applied
        self.id = newID  # uuid.UUID or None for a null id
        self.skill = 0.0
        self.nation = ""
        self.properties = {}

    def clone(self):
        a = XkorAthlete(self.id)
        a.name = self.name
        a.rpBonus = self.rpBonus
        a.rpSkill = self.rpSkill
        a.skill = self.skill
        a.nation = self.nation
        a.properties = copy.copy(self.properties)
        return a

    def property(self, key):
        if key == "name":
            return self.name
        elif key == "id":
            return "{%s}" % self.id if self.id is not None else ""
        elif key == "nation":
            return self.nation
        elif key == "skill":
            return self.skill
        else:
            return self.properties.get(key)

    def setProperty(self, key, value):
        import uuid as _uuid

        if key == "name":
            self.name = toString(value)
        elif key == "id":
            self.id = _uuid.UUID(toString(value).strip("{}"))
        elif key == "nation":
            self.nation = toString(value)
        elif key == "skill":
            self.skill = toDouble(value)
        else:
            self.properties[key] = value

    def __lt__(self, that):
        a = self.id.int if self.id is not None else -1
        b = that.id.int if that.id is not None else -1
        return a < b

    def __eq__(self, that):
        return isinstance(that, XkorAthlete) and self.id == that.id

    def __hash__(self):
        return hash(self.id)
