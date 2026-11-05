from PySide6.QtWidgets import QCheckBox, QFormLayout

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget


class XkorSingleEliminationCompetitionOptions(XkorAbstractOptionsWidget):
    """Options for a knockout bracket.

    Seeding deliberately isn't here: the draw is arranged on the bracket page
    itself, where the user can see the pairings and rearrange them, so there
    is nothing to choose up front.
    """

    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.thirdPlace = QCheckBox("Third-place playoff")
        self.thirdPlace.setChecked(self._optionIsTrue("thirdPlacePlayoff"))
        self.thirdPlace.setToolTip(
            "Add an extra round, played before the final, between the two "
            "beaten semi-finalists.")
        self.thirdPlace.stateChanged.connect(self.setThirdPlacePlayoff)

        layout = QFormLayout(self)
        layout.addRow("", self.thirdPlace)

        self.setThirdPlacePlayoff(self.thirdPlace.checkState())

    def setThirdPlacePlayoff(self, value):
        self._setFlag("thirdPlacePlayoff", value)
