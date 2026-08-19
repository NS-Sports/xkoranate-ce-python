from ...variant import toString
from .abstractresultcomparator import XkorAbstractResultComparator


class XkorBasicResultComparator(XkorAbstractResultComparator):
    def __init__(self, type, opt):
        if toString(opt.get("sortOrder", "ascending")) == "ascending":
            self.isAscending = True
        else:
            self.isAscending = False

    def __call__(self, a, b):
        if self.isAscending:
            return a.score() < b.score()
        else:
            return b.score() < a.score()

    # every comparator sorts through sortKey(), which dispatches back into
    # this instance's __call__ — the C++ original had to redeclare sort() in
    # each subclass because qSort was instantiated on the concrete type
    # (XkorTimedResultComparator's used std::stable_sort, which is what
    # Python's sort already gives us; the rest used plain std::sort)
    def sort(self, res):
        res.sort(key=self.sortKey())
