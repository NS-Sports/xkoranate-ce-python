class XkorTableColumn:
    def __init__(self, ct="", h="", w=0):
        self.columnType = ct
        self.heading = h
        self.width = w


def standingsColumns(sortCriteria, heading, nameHeading, nameWidth, positionWidth,
                     matchdayWidth, draws, overtime=False, gridWidth=None):
    """A standings table's columns, in order. heading(columnType) names each
    counted column; the goal, win-percentage and points columns appear only
    for the sort criteria that use them, and the results grid only given a
    gridWidth."""
    columns = [XkorTableColumn("position", "", positionWidth),
               XkorTableColumn("name", nameHeading, nameWidth)]

    def add(columnType, width):
        columns.append(XkorTableColumn(columnType, heading(columnType), width))

    add("played", matchdayWidth + 2)
    add("wins", matchdayWidth + 2)
    if draws:
        add("draws", matchdayWidth + 1)
    add("losses", matchdayWidth + 1)
    if overtime:
        for columnType in ("otWins", "soWins", "otLosses", "soLosses"):
            add(columnType, matchdayWidth + 2)
    if any(c in sortCriteria for c in ("goalAverage", "goalDifference", "goalsAgainst", "goalsFor")):
        add("goalsFor", matchdayWidth + 3)
        add("goalsAgainst", matchdayWidth + 2)
    if "goalAverage" in sortCriteria:
        add("goalAverage", 7)
    if "goalDifference" in sortCriteria:
        add("goalDifference", matchdayWidth + 2)
    for columnType in ("winPercent", "winPercentPure", "winPercentNFL"):
        if columnType in sortCriteria:
            add(columnType, 8)
    if "points" in sortCriteria:
        add("points", matchdayWidth + 3)
    if gridWidth is not None:
        columns.append(XkorTableColumn("resultsGrid", "", gridWidth))
    return columns
