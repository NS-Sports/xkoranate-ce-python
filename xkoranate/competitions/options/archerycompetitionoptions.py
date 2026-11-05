from xkoranate.competitions.options.cutoffoptions import XkorCutoffOptions


class XkorArcheryCompetitionOptions(XkorCutoffOptions):
    cutoffLabel = "Archers advancing to next round"
    initialText = "<small>All ties will be settled by lots.</small>"
    noCutoffText = initialText
    cutoffText = ("<small>A tie for %s place will be settled by tiebreak arrows. "
                  "All other ties will be settled by drawing lots.")
