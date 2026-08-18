from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QFormLayout, QVBoxLayout, QWidget)

from ..signuplist import XkorSignupList
from ..ui.tooltips import wrapped_tooltip
from ..ui.typography import heading_label

# per-athlete skill-entry ceiling used whenever "Maximum skill" isn't a
# manually-set bound (pinned to participants, or fixed for raw-rank
# paradigms) -- generous enough that entering a new highest-ranked
# participant is never blocked by a stale/irrelevant cap
_ENTRY_SKILL_CEILING = 9999.999


def _cloneSignupList(sl):
    # XkorSignupList is passed/returned by value in the C++
    rval = XkorSignupList()
    rval.ath = [a.clone() for a in sl.ath]
    rval.min = sl.min
    rval.max = sl.max
    return rval


class XkorSignupListEditor(QWidget):
    dataChanged = Signal()
    itemDeleted = Signal(object)  # QUuid
    signupListDirectoryChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.isLoading = False

        self.athletes = None
        self.m_data = XkorSignupList()
        self._usesMinSkill = True
        self._usesMaxSkill = True

        label = heading_label("Set participants", level=1, center=True)

        # minimum rank
        self.minRank = QDoubleSpinBox()
        self.minRank.setDecimals(3)
        self.minRank.setRange(-999.999, 1)
        self.minRank.valueChanged.connect(self.minRankChanged)

        # maximum rank
        self.maxRank = QDoubleSpinBox()
        self.maxRank.setDecimals(3)
        # range must be set before value: a fresh QDoubleSpinBox defaults to
        # [0, 99.99], so setValue(100) before widening the range silently
        # clamped the intended default down to 99.99
        self.maxRank.setRange(0, 9999.999)
        self.maxRank.setValue(100)
        self.maxRank.valueChanged.connect(self.maxRankChanged)

        # lets max rank auto-follow the highest entered participant instead
        # of acting as a pre-set ceiling that clamps entries
        self.pinMaxToParticipants = QCheckBox("Pin to max participant rank")
        self.pinMaxToParticipants.setToolTip(wrapped_tooltip(
            "Maximum skill automatically tracks the highest entered participant, instead of "
            "acting as a ceiling that blocks entering anyone above it."))
        self.pinMaxToParticipants.stateChanged.connect(self._pinMaxToParticipantsChanged)

        # form layout
        self.form = QFormLayout()
        self.form.addRow("Minimum skill:", self.minRank)
        self.form.addRow("Maximum skill:", self.maxRank)
        self.form.addRow("", self.pinMaxToParticipants)

        # layout
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(label, 0, Qt.AlignCenter)
        self.layout.addLayout(self.form, 0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.minRank.valueChanged.connect(self.setDataChanged)
        self.maxRank.valueChanged.connect(self.setDataChanged)
        self.pinMaxToParticipants.stateChanged.connect(self.setDataChanged)

    def data(self):
        self.updateData()
        return _cloneSignupList(self.m_data)

    def _maxRankMode(self):
        """"fixed": paradigm calibrates itself (e.g. LISA's refRank) and
        needs a true pass-through, not a rescale. "pinned": paradigm's
        outcome is invariant to max, so just auto-follow participants
        rather than requiring the organizer to set (and clamp against) a
        ceiling. "manual": today's existing organizer-set-ceiling behavior."""
        if not self._usesMinSkill and not self._usesMaxSkill:
            return "fixed"
        if not self._usesMaxSkill or self.pinMaxToParticipants.isChecked():
            return "pinned"
        return "manual"

    def _applyMaxRankMode(self):
        mode = self._maxRankMode()
        if mode == "fixed":
            self.maxRank.setValue(1.0)
        elif mode == "pinned":
            self._updatePinnedMax()
        self.maxRank.setEnabled(mode == "manual")
        if self.athletes:
            self.athletes.setMaxRank(
                self.maxRank.value() if mode == "manual" else _ENTRY_SKILL_CEILING)

    def _updatePinnedMax(self):
        if not self.athletes:
            return
        skills = [a.skill for a in self.athletes.athletes()]
        if not skills:
            return
        pinnedMax = max(skills)
        if pinnedMax <= self.minRank.value():
            # adjustRank() divides by (max - min); since these paradigms are
            # invariant to max's actual value (see usesMaxSkill()), nudging
            # it above min is always safe and avoids a ZeroDivisionError
            # when every entered skill is still at (or equals) the min, e.g.
            # a freshly-added participant row defaulting to skill 0
            pinnedMax = self.minRank.value() + 1.0
        self.maxRank.setValue(pinnedMax)

    def _onAthleteListChanged(self):
        if self._maxRankMode() == "pinned":
            self._updatePinnedMax()

    def _pinMaxToParticipantsChanged(self, _state):
        self._applyMaxRankMode()

    def maxRankChanged(self, newMax):
        # min rank can’t be higher than max rank
        self.minRank.setMaximum(newMax)

        # inform the athlete widget (only in manual mode -- pinned/fixed
        # modes keep the entry ceiling generous, see _applyMaxRankMode)
        if self.athletes and self._maxRankMode() == "manual":
            self.athletes.setMaxRank(newMax)

    def minRankChanged(self, newMin):
        # max rank can’t be lower than min rank
        self.maxRank.setMinimum(newMin)

        # inform the athlete widget
        if self.athletes:
            self.athletes.setMinRank(newMin)

    def setData(self, data):
        data = _cloneSignupList(data)

        self.isLoading = True  # prevent dataChanged from being emitted

        if not self._usesMinSkill:
            # this paradigm mandates min=0 (e.g. LISA needs a true identity
            # pass-through) regardless of whatever was persisted -- an older
            # save, or one from before this paradigm's min/max semantics
            # existed, would otherwise silently reintroduce a rescale that
            # setSport() already went to the trouble of correcting
            data.setMinRank(0.0)

        self.minRank.setValue(data.minRank())
        self.maxRank.setValue(data.maxRank())
        if self.athletes:
            self.athletes.setMinRank(data.minRank())
            self.athletes.setMaxRank(data.maxRank())
            self.athletes.setAthletes(data.athletes())

        self.m_data = data

        # re-derive max (fixed/pinned/manual) from the CURRENT paradigm
        # rather than trusting whatever max was persisted in `data`, then
        # sync the correction back into m_data -- still while isLoading, so
        # this internal correction doesn't mark the event as modified just
        # from loading it
        self._applyMaxRankMode()
        self.updateData()

        self.isLoading = False  # allow dataChanged to be emitted if the user does stuff

    def setDataChanged(self):
        if not self.isLoading:
            self.dataChanged.emit()

    def setItemDeleted(self, id):
        self.itemDeleted.emit(id)

    def setSignupListDirectory(self, dir):
        self.signupListDirectoryChanged.emit(dir)

    def setSport(self, sport, paradigmOptions):
        self.updateData()

        if self.athletes:
            self.layout.removeWidget(self.athletes)
        if self.athletes is not None:  # delete athletes
            self.athletes.setParent(None)
            self.athletes.deleteLater()

        from ..paradigms.paradigmfactory import XkorParadigmFactory

        p = XkorParadigmFactory.newParadigmForSport(sport, paradigmOptions)

        usesMin = p.usesMinSkill()
        usesMax = p.usesMaxSkill()
        # setSport() is re-invoked on every paradigm-*options* change too
        # (e.g. toggling home advantage), not just on an actual sport
        # change -- only reset the pin checkbox/forced bounds when the
        # paradigm's skill-bound capabilities actually changed, so we don't
        # clobber a manual pin choice the user made in "manual" mode
        capabilitiesChanged = (usesMin, usesMax) != (self._usesMinSkill, self._usesMaxSkill)
        self._usesMinSkill = usesMin
        self._usesMaxSkill = usesMax

        if capabilitiesChanged:
            if not usesMin and not usesMax:
                # e.g. LISA: the paradigm supplies its own calibration
                # (reference rank), so force a true pass-through --
                # adjustRank((r-0)/(1-0)) == r -- rather than silently
                # rescaling raw rank against a leftover/arbitrary ceiling
                self.m_data.setMinRank(0.0)
                self.m_data.setMaxRank(1.0)
                self.pinMaxToParticipants.setChecked(False)
            elif not usesMax:
                # e.g. SQIS/Footba11er/Howzzat: outcome is invariant to max,
                # so auto-follow the entered participants instead of
                # requiring (and clamping entries against) a pre-set ceiling
                self.pinMaxToParticipants.setChecked(True)
            else:
                self.pinMaxToParticipants.setChecked(False)

        self.form.setRowVisible(self.minRank, self._usesMinSkill)
        self.form.setRowVisible(self.maxRank, self._usesMaxSkill)
        self.form.setRowVisible(self.pinMaxToParticipants, self._usesMaxSkill)

        self.athletes = p.newAthleteWidget()
        self.setData(self.m_data)
        self.layout.addWidget(self.athletes, 1)
        self.athletes.listChanged.connect(self.setDataChanged)
        self.athletes.listChanged.connect(self._onAthleteListChanged)
        self.athletes.itemDeleted.connect(self.setItemDeleted)
        self.athletes.signupListDirectoryChanged.connect(self.setSignupListDirectory)

        # re-apply now that a fresh athlete widget/data exist
        self._applyMaxRankMode()

    def updateData(self):
        self.m_data.setMinRank(self.minRank.value())
        self.m_data.setMaxRank(self.maxRank.value())
        if self.athletes:
            self.m_data.setAthletes(self.athletes.athletes())
