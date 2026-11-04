def crossAdjustment(row, w, d, l, cross, otW=None, soW=None, otL=None, soL=None):
    """Points to swap in for games against other conferences.

    cross is (win, draw, loss) for those games, or None to score every game
    alike. The row's regular counts already include cross games at the
    ordinary rate, so this adds the difference. An OT/SO result follows the
    cross win/loss points too, unless its own points were set (otW and the
    rest are the raw overrides, None when not set).
    """
    if cross is None:
        return 0
    cw, cd, cl = cross
    rval = (row.crossWins() * (cw - w) + row.crossDraws() * (cd - d)
            + row.crossLosses() * (cl - l))
    for decider, won, override in (("OT", True, otW), ("SO", True, soW),
                                   ("OT", False, otL), ("SO", False, soL)):
        if override is None:
            rval += row.crossDecided(decider, won) * ((cw - w) if won else (cl - l))
    return rval


class XkorPointsScheme:
    """What each result is worth, shared by a table and its sorter."""

    def __init__(self):
        self.win = 0.0
        self.draw = 0.0
        self.loss = 0.0
        # None means "not overridden": fall back to win/loss so tables that
        # never use OT/SO deciders score exactly as before
        self.otWin = None
        self.soWin = None
        self.otLoss = None
        self.soLoss = None
        self.cross = None  # (win, draw, loss) v other conferences

    def raw(self):
        """(OT win, SO win, OT loss, SO loss) as set, None where not."""
        return (self.otWin, self.soWin, self.otLoss, self.soLoss)

    def resolved(self):
        """The same four with the win/loss fallback applied."""
        return (self.win if self.otWin is None else self.otWin,
                self.win if self.soWin is None else self.soWin,
                self.loss if self.otLoss is None else self.otLoss,
                self.loss if self.soLoss is None else self.soLoss)

    def pointsFor(self, row):
        otW, soW, otL, soL = self.resolved()
        return (row.regulationWins() * self.win + row.draws() * self.draw
                + row.regulationLosses() * self.loss
                + row.otWins() * otW + row.soWins() * soW
                + row.otLosses() * otL + row.soLosses() * soL
                + crossAdjustment(row, self.win, self.draw, self.loss, self.cross, *self.raw()))


class XkorPointsAccessors:
    """The named points getters and setters, for a class keeping its
    XkorPointsScheme in self.points. Some callers look them up by name."""

    def getPointsForWin(self):
        return self.points.win

    def getPointsForDraw(self):
        return self.points.draw

    def getPointsForLoss(self):
        return self.points.loss

    def getPointsForOTWin(self):
        return self.points.resolved()[0]

    def getPointsForSOWin(self):
        return self.points.resolved()[1]

    def getPointsForOTLoss(self):
        return self.points.resolved()[2]

    def getPointsForSOLoss(self):
        return self.points.resolved()[3]

    # the raw getters return None where the getPointsFor*() ones above resolve
    # the fallback, so a caller that needs to tell "not overridden" apart from
    # "overridden to the same number" — the XML writer, and the widget deciding
    # whether its spin box still mirrors the win/loss one — can do so. Writing
    # a resolved value out would pin it, silently breaking the fallback the
    # next time the file is opened.
    def getRawPointsForOTWin(self):
        return self.points.otWin

    def getRawPointsForSOWin(self):
        return self.points.soWin

    def getRawPointsForOTLoss(self):
        return self.points.otLoss

    def getRawPointsForSOLoss(self):
        return self.points.soLoss

    def setCrossPoints(self, points):
        """(win, draw, loss) for games between conferences, or None to
        score them like any other game."""
        self.points.cross = None if points is None else tuple(points)

    def setPointsForWin(self, pts):
        self.points.win = pts

    def setPointsForDraw(self, pts):
        self.points.draw = pts

    def setPointsForLoss(self, pts):
        self.points.loss = pts

    # pass None to clear an override and go back to following the win /
    # loss points
    def setPointsForOTWin(self, pts):
        self.points.otWin = pts

    def setPointsForSOWin(self, pts):
        self.points.soWin = pts

    def setPointsForOTLoss(self, pts):
        self.points.otLoss = pts

    def setPointsForSOLoss(self, pts):
        self.points.soLoss = pts
