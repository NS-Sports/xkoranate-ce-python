from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QFormLayout, QLabel, QRadioButton, QWidget

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.ui.tooltips import wrapped_tooltip
from xkoranate.variant import toString

from .collapsiblesection import XkorCollapsibleSection

_DEFAULT_HOME_ADVANTAGE_EAR = 100.0
_DEFAULT_POWER_SCALAR = 1.984
_DEFAULT_REF_RANK = 10.93
_DEFAULT_REAR = 300.0
_DEFAULT_MARGIN_DIVISOR = 750.0


class XkorLISAParadigmOptions(XkorAbstractOptionsWidget):
    """Per-event overrides for LISA. Every constant the algorithm's author
    calls out as adjustable (power scalar, reference rank, REAR, margin
    divisor) gets its own spinbox here, same as home-advantage magnitude
    already had — unlike SQIS/NSFS, LISA has no maxRank/maxSkill concept, so
    there's nothing else paradigm-specific to surface."""

    def __init__(self, opts, defaultHomeAdvantageEAR=_DEFAULT_HOME_ADVANTAGE_EAR,
                 defaultPowerScalar=_DEFAULT_POWER_SCALAR, defaultRefRank=_DEFAULT_REF_RANK,
                 defaultREAR=_DEFAULT_REAR, defaultMarginDivisor=_DEFAULT_MARGIN_DIVISOR,
                 parent=None):
        super().__init__(opts, parent)

        self.homeAdvantage = self._flagCheckBox("homeAdvantage", "Apply home advantage",
                                                self._optionIsTrue("homeAdvantage"))

        self.homeAdvantageEARLabel = QLabel("Home advantage (EAR):")
        self.homeAdvantageEAR = self._constantSpinBox(
            "homeAdvantageEAR", defaultHomeAdvantageEAR, decimals=1, minimum=0, maximum=500, step=5)

        self._updateHomeAdvantageEAREnabled(self.homeAdvantage.checkState())
        self.homeAdvantage.stateChanged.connect(self._updateHomeAdvantageEAREnabled)

        # home advantage mode: "Fixed" is the EAR magnitude above, used
        # directly for every match (today's only behaviour). The other two
        # let each team set its own rating as a participant column instead
        # -- the EAR field above stops being the direct value and becomes
        # the baseline/default those ratings are computed against, so it
        # stays visible and relevant in every mode rather than being hidden.
        # Full explanations live in tooltips, not the labels -- this panel
        # has to fit a small default window.
        self.homeAdvantageModeFixed = QRadioButton("Fixed")
        self.homeAdvantageModeFixed.setToolTip(wrapped_tooltip(
            "Same home advantage for every match."))
        self.homeAdvantageModeAdversarial = QRadioButton("Adversarial (per-team)")
        self.homeAdvantageModeAdversarial.setToolTip(wrapped_tooltip(
            "Each team sets its own -5 to +5 rating; the two teams' ratings combine, so "
            "boosting your own home advantage also raises what you hand opponents when you "
            "visit them. Self-limiting -- suits player-vs-player competition."))
        self.homeAdvantageModeIndividual = QRadioButton("Individual (per-team, uncapped)")
        self.homeAdvantageModeIndividual.setToolTip(wrapped_tooltip(
            "Each team's own rating applies only when they're home, uncapped, with no effect "
            "on the away side. Not self-limiting -- suits domestic leagues, where home "
            "advantage doesn't need to be zero-sum."))

        self.homeAdvantageModeGroup = QButtonGroup()
        self.homeAdvantageModeGroup.addButton(self.homeAdvantageModeFixed)
        self.homeAdvantageModeGroup.addButton(self.homeAdvantageModeAdversarial)
        self.homeAdvantageModeGroup.addButton(self.homeAdvantageModeIndividual)

        currentMode = toString(self.options.get("homeAdvantageMode", "fixed"))
        if currentMode == "adversarial":
            self.homeAdvantageModeAdversarial.setChecked(True)
        elif currentMode == "individual":
            self.homeAdvantageModeIndividual.setChecked(True)
        else:
            self.homeAdvantageModeFixed.setChecked(True)
        self.setHomeAdvantageMode()  # populate self.options from whichever button ended up checked
        self.homeAdvantageModeGroup.idClicked.connect(self.setHomeAdvantageMode)

        homeAdvantageModeForm = QFormLayout()
        homeAdvantageModeForm.addRow(self.homeAdvantageModeFixed)
        homeAdvantageModeForm.addRow(self.homeAdvantageModeAdversarial)
        homeAdvantageModeForm.addRow(self.homeAdvantageModeIndividual)

        # QFormLayout sucks, so we create our own label
        self.homeAdvantageModeLabel = QLabel("Home advantage mode:")
        self.homeAdvantageModeLabel.setContentsMargins(0, -4, 0, 0)

        self._updateHomeAdvantageModeEnabled(self.homeAdvantage.checkState())
        self.homeAdvantage.stateChanged.connect(self._updateHomeAdvantageModeEnabled)

        # LISA formula constants: rank/EAR conversion (power scalar, reference
        # rank, REAR) and margin shaping (margin divisor). These are always
        # active (no enable/disable toggle like home advantage has).
        self.powerScalar = self._constantSpinBox(
            "powerScalar", defaultPowerScalar, decimals=3, minimum=0.1, maximum=5.0, step=0.01)
        self.refRank = self._constantSpinBox(
            "refRank", defaultRefRank, decimals=2, minimum=0.01, maximum=1000.0, step=0.1)
        self.rear = self._constantSpinBox(
            "REAR", defaultREAR, decimals=1, minimum=1.0, maximum=2000.0, step=5.0)
        self.marginDivisor = self._constantSpinBox(
            "marginDivisor", defaultMarginDivisor,
            decimals=1, minimum=1.0, maximum=5000.0, step=10.0)

        self.showTLAs = self._flagCheckBox("showTLAs", "Show team names",
                                           self._optionIsTrue("showTLAs", True))

        advancedContent = QWidget()
        advancedForm = QFormLayout(advancedContent)
        advancedForm.setContentsMargins(0, 4, 0, 0)
        advancedForm.addRow("Power scalar:", self.powerScalar)
        advancedForm.addRow("Reference rank:", self.refRank)
        advancedForm.addRow("REAR:", self.rear)
        advancedForm.addRow("Margin divisor:", self.marginDivisor)

        self.advancedSection = XkorCollapsibleSection("Advanced options")
        self.advancedSection.setContent(advancedContent)

        self.form = QFormLayout(self)
        self.form.addRow("", self.homeAdvantage)
        self.form.addRow(self.homeAdvantageEARLabel, self.homeAdvantageEAR)
        self.form.addRow(self.homeAdvantageModeLabel, homeAdvantageModeForm)
        self.form.addRow("", self.showTLAs)
        self.form.addRow(self.advancedSection)

    def _updateHomeAdvantageEAREnabled(self, x):
        enabled = Qt.CheckState(x) == Qt.Checked
        self.homeAdvantageEARLabel.setEnabled(enabled)
        self.homeAdvantageEAR.setEnabled(enabled)

    def setHomeAdvantageMode(self, *_args):
        checkedButton = self.homeAdvantageModeGroup.checkedButton()
        if checkedButton is self.homeAdvantageModeAdversarial:
            self.options["homeAdvantageMode"] = "adversarial"
        elif checkedButton is self.homeAdvantageModeIndividual:
            self.options["homeAdvantageMode"] = "individual"
        else:
            self.options["homeAdvantageMode"] = "fixed"
        self.optionsChanged.emit(self.options)

    def _updateHomeAdvantageModeEnabled(self, x):
        enabled = Qt.CheckState(x) == Qt.Checked
        self.homeAdvantageModeLabel.setEnabled(enabled)
        self.homeAdvantageModeFixed.setEnabled(enabled)
        self.homeAdvantageModeAdversarial.setEnabled(enabled)
        self.homeAdvantageModeIndividual.setEnabled(enabled)
