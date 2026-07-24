def _points(row, w, d, l, otW, soW, otL, soL):
    return (row.regulationWins() * w + row.draws() * d + row.regulationLosses() * l
            + row.otWins() * otW + row.soWins() * soW
            + row.otLosses() * otL + row.soLosses() * soL)


class XkorSortPointsGr:
    def __init__(self, w, d, l, otW=None, soW=None, otL=None, soL=None):
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
                        self.pointsForOTLoss, self.pointsForSOLoss)
                > _points(b, self.pointsForWin, self.pointsForDraw, self.pointsForLoss,
                         self.pointsForOTWin, self.pointsForSOWin,
                         self.pointsForOTLoss, self.pointsForSOLoss))


class XkorSortPointsEq:
    def __init__(self, w, d, l, otW=None, soW=None, otL=None, soL=None):
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
                        self.pointsForOTLoss, self.pointsForSOLoss)
                == _points(b, self.pointsForWin, self.pointsForDraw, self.pointsForLoss,
                          self.pointsForOTWin, self.pointsForSOWin,
                          self.pointsForOTLoss, self.pointsForSOLoss))
