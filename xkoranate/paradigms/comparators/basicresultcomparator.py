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
            return self.sortAscending(a, b)
        else:
            return self.sortAscending(b, a)

    def sortAscending(self, a, b):
        """Does a come before b when the sort runs ascending? Subclasses
        add their tiebreaks here; __call__ flips it for descending sorts."""
        return a.score() < b.score()

    # every comparator sorts through sortKey(), which dispatches back into
    # this instance's __call__ — the C++ original had to redeclare sort() in
    # each subclass because qSort was instantiated on the concrete type
    # (XkorTimedResultComparator's used std::stable_sort, which is what
    # Python's sort already gives us; the rest used plain std::sort)
    def sort(self, res):
        res.sort(key=self.sortKey())
