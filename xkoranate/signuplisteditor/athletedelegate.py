from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QDoubleSpinBox, QItemDelegate, QLineEdit

from ..variant import toDouble, toString


class XkorAthleteDelegate(QItemDelegate):
    def __init__(self, columnTypes, minDouble, maxDouble, doubleStep, parent=None):
        super().__init__(parent)
        self.m_columnTypes = list(columnTypes)
        self.m_minDouble = minDouble
        self.m_maxDouble = maxDouble
        self.m_doubleStep = doubleStep
        self.minRank = 0
        self.maxRank = 1

    def createEditor(self, parent, option, index):
        if self.m_columnTypes[index.column()] == "double":
            spinBox = QDoubleSpinBox(parent)
            spinBox.setAlignment(Qt.AlignRight)
            spinBox.setDecimals(3)
            spinBox.setMinimum(self.m_minDouble)
            spinBox.setMaximum(self.m_maxDouble)
            spinBox.setSingleStep(self.m_doubleStep)
            spinBox.setFrame(False)
            return spinBox
        elif self.m_columnTypes[index.column()] == "golfStyle":
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)

            # QRegExpValidator was removed in Qt 6; QRegularExpressionValidator
            # has the same exact-match semantics
            r = QRegularExpression("[1-6]{6}")
            validator = QRegularExpressionValidator(r, lineEdit)
            lineEdit.setValidator(validator)

            return lineEdit
        elif self.m_columnTypes[index.column()] == "skill":
            spinBox = QDoubleSpinBox(parent)
            spinBox.setAlignment(Qt.AlignRight)
            spinBox.setDecimals(3)
            spinBox.setMinimum(self.minRank)
            spinBox.setMaximum(self.maxRank)
            spinBox.setSingleStep(0.01)
            spinBox.setFrame(False)
            return spinBox
        elif self.m_columnTypes[index.column()] == "homeAdvantage":
            # LISA's per-team home advantage rating: always 0-100,
            # regardless of this widget's generic double/skill ranges
            spinBox = QDoubleSpinBox(parent)
            spinBox.setAlignment(Qt.AlignRight)
            spinBox.setDecimals(0)
            spinBox.setMinimum(0)
            spinBox.setMaximum(100)
            spinBox.setSingleStep(5)
            spinBox.setFrame(False)
            return spinBox
        else:
            lineEdit = QLineEdit(parent)
            lineEdit.setFrame(False)
            return lineEdit

    def setEditorData(self, editor, index):
        if self.m_columnTypes[index.column()] in ("double", "skill", "homeAdvantage"):
            spinBox = editor
            spinBox.setValue(toDouble(index.model().data(index, Qt.DisplayRole)))
        else:
            lineEdit = editor
            lineEdit.setText(toString(index.model().data(index, Qt.DisplayRole)))

    def setMaxRank(self, newMax):
        self.maxRank = newMax

    def setMinRank(self, newMin):
        self.minRank = newMin

    def setModelData(self, editor, model, index):
        if self.m_columnTypes[index.column()] in ("double", "skill", "homeAdvantage"):
            spinBox = editor
            model.setData(index, spinBox.value())
        else:
            lineEdit = editor
            model.setData(index, lineEdit.text())
