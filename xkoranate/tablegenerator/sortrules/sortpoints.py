def _points(row, w, d, l, otW, soW, otL, soL, cross=None, raw=(None, None, None, None)):
    rval = (row.regulationWins() * w + row.draws() * d + row.regulationLosses() * l
            + row.otWins() * otW + row.soWins() * soW
            + row.otLosses() * otL + row.soLosses() * soL)
    return rval + crossAdjustment(row, w, d, l, cross, *raw)


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


class XkorSortPointsGr:
    def __init__(self, w, d, l, otW=None, soW=None, otL=None, soL=None, cross=None,
                 raw=(None, None, None, None)):
        self.crossPoints = cross
        # the OT/SO overrides as set, None where they follow win/loss
        self.raw = raw
        self.pointsForWin = w
        self.pointsForDraw = d
        self.pointsForLoss = l
        self.pointsForOTWin = otW if otW is not None else w
        self.pointsForSOWin = soW if soW is not None else w
        self.pointsForOTLoss = otL if otL is not None else l
        self.pointsForSOLoss = soL if soL is not None else l

    def __call__(self, a, b):
        return (_points(a, self.pointsForWin, self.pointsForDraw, self.pointsForLoss,
                        self.pointsForOTWin, self.pointsForSOWin,
                        self.pointsForOTLoss, self.pointsForSOLoss, self.crossPoints, self.raw)
                > _points(b, self.pointsForWin, self.pointsForDraw, self.pointsForLoss,
                         self.pointsForOTWin, self.pointsForSOWin,
                         self.pointsForOTLoss, self.pointsForSOLoss, self.crossPoints, self.raw))


class XkorSortPointsEq:
    def __init__(self, w, d, l, otW=None, soW=None, otL=None, soL=None, cross=None,
                 raw=(None, None, None, None)):
        self.crossPoints = cross
        # the OT/SO overrides as set, None where they follow win/loss
        self.raw = raw
        self.pointsForWin = w
        self.pointsForDraw = d
        self.pointsForLoss = l
        self.pointsForOTWin = otW if otW is not None else w
        self.pointsForSOWin = soW if soW is not None else w
        self.pointsForOTLoss = otL if otL is not None else l
        self.pointsForSOLoss = soL if soL is not None else l

    def __call__(self, a, b):
        return (_points(a, self.pointsForWin, self.pointsForDraw, self.pointsForLoss,
                        self.pointsForOTWin, self.pointsForSOWin,
                        self.pointsForOTLoss, self.pointsForSOLoss, self.crossPoints, self.raw)
                == _points(b, self.pointsForWin, self.pointsForDraw, self.pointsForLoss,
                          self.pointsForOTWin, self.pointsForSOWin,
                          self.pointsForOTLoss, self.pointsForSOLoss, self.crossPoints, self.raw))
