from xkoranate.competitions.options.cutoffoptions import XkorCutoffOptions

_FINAL = "In the final round, only ties for medal positions will be settled by shoot-offs.</small>"


class XkorShootingCompetitionOptions(XkorCutoffOptions):
    cutoffLabel = "Shooters advancing to final"
    initialText = "<small>In the qualifying round, all ties will be unresolved.<br/>" + _FINAL
    noCutoffText = "<small>In the qualifying round, all ties will be left unresolved.<br/>" + _FINAL
    cutoffText = ("<small>In the qualifying round, only a tie for %s place will be settled by a "
                  "shoot-off.<br/>" + _FINAL)
