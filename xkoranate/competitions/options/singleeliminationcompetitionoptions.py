from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toString


class XkorSingleEliminationCompetitionOptions(XkorAbstractOptionsWidget):
    """Options for a knockout bracket.

    Seeding deliberately isn't here: the draw is arranged on the bracket page
    itself, where the user can see the pairings and rearrange them, so there
    is nothing to choose up front.
    """

    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.thirdPlace = QCheckBox("Third-place playoff")
        self.thirdPlace.setChecked(toString(self.options.get("thirdPlacePlayoff", "false")) == "true")
        self.thirdPlace.setToolTip(
            "Add an extra round, played before the final, between the two "
            "beaten semi-finalists.")
        self.thirdPlace.stateChanged.connect(self.setThirdPlacePlayoff)

        layout = QFormLayout(self)
        layout.addRow("", self.thirdPlace)

        self.options["thirdPlacePlayoff"] = "true" if self.thirdPlace.isChecked() else "false"

    def setThirdPlacePlayoff(self, value):
        if isinstance(value, Qt.CheckState):
            value = value.value
        self.options["thirdPlacePlayoff"] = (
            "true" if value == Qt.CheckState.Checked.value else "false")
        self.optionsChanged.emit(self.options)
