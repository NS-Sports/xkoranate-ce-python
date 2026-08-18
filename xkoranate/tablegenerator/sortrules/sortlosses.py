class XkorSortLossesGr:
    def __call__(self, a, b):
        return a.losses() < b.losses()


class XkorSortLossesEq:
    def __call__(self, a, b):
        return a.losses() == b.losses()
