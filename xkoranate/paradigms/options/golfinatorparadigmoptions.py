import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QGridLayout, QHeaderView, QTableWidget,
                               QTableWidgetItem)

from xkoranate.abstractoptionswidget import XkorAbstractOptionsWidget
from xkoranate.variant import toDouble, toList, toString


class XkorGolfinatorParadigmOptions(XkorAbstractOptionsWidget):
    def __init__(self, opts, parent=None):
        super().__init__(opts, parent)

        self.course = QTableWidget()
        self.course.setColumnCount(7)
        self.course.setRowCount(18)
        self.course.setHorizontalHeaderLabels(["Yards", "Par", "Differential", "Sand", "Water", "Narrow", "Green"])
        self.course.setVerticalHeaderLabels(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18"])

        self.course.setGridStyle(Qt.NoPen)
        self.course.setAlternatingRowColors(True)

        self.course.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        f = QFont()
        metrics = QFontMetrics(f)
        self.course.verticalHeader().setDefaultSectionSize(metrics.height() + 2)

        layout = QGridLayout(self)
        layout.addWidget(self.course, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)

        # set values
        yardage = toList(self.options.get("yardage", self.defaultValue("yardage")))
        par = toList(self.options.get("par", self.defaultValue("par")))
        differential = toList(self.options.get("differential", self.defaultValue("differential")))
        sand = toList(self.options.get("sand", self.defaultValue("sand")))
        water = toList(self.options.get("water", self.defaultValue("water")))
        narrow = toList(self.options.get("narrow", self.defaultValue("narrow")))
        green = toList(self.options.get("green", self.defaultValue("green")))

        for i in range(len(yardage)):
            self.course.setItem(i, 0, QTableWidgetItem(toString(yardage[i])))
        for i in range(len(par)):
            self.course.setItem(i, 1, QTableWidgetItem(toString(par[i])))
        for i in range(len(differential)):
            self.course.setItem(i, 2, QTableWidgetItem(toString(differential[i])))
        for i in range(len(sand)):
            self.course.setItem(i, 3, QTableWidgetItem(toString(sand[i])))
        for i in range(len(water)):
            self.course.setItem(i, 4, QTableWidgetItem(toString(water[i])))
        for i in range(len(narrow)):
            self.course.setItem(i, 5, QTableWidgetItem(toString(narrow[i])))
        for i in range(len(green)):
            self.course.setItem(i, 6, QTableWidgetItem(toString(green[i])))

        self.course.cellChanged.connect(self.updateData)

    def defaultValue(self, column):
        if column == "yardage":
            return [435, 529, 198, 517, 451, 408, 178, 457, 414, 495, 505, 155, 614, 435, 478, 381, 455, 357]
        elif column == "par":
            return [4, 5, 3, 5, 4, 4, 3, 4, 4, 4, 4, 3, 5, 4, 4, 4, 4, 4]
        elif column == "differential":
            return [0.19, -0.36, 0.15, 0, 0.23, 0.19, 0.24, 0.13, 0.18, 0.23, 0.32, 0.3, -0.14, 0.25, 0.35, 0.19, 0.63, -0.46]
        elif column == "sand":
            return [1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0]
        elif column == "water":
            return [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
        elif column == "narrow":
            return [0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0]
        elif column == "green":
            return [0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0]
        else:
            return []

    def updateData(self, row, column):
        columnName = ""
        if column == 0:
            columnName = "yardage"
        elif column == 1:
            columnName = "par"
        elif column == 2:
            columnName = "differential"
        elif column == 3:
            columnName = "sand"
        elif column == 4:
            columnName = "water"
        elif column == 5:
            columnName = "narrow"
        elif column == 6:
            # the C++ stored this as "grass", which the paradigm never reads
            columnName = "green"
        else:
            print("non-existent column edited in XkorGolfinatorParadigmOptions::updateData(int, int)", file=sys.stderr)

        columnValues = toList(self.options.get(columnName, self.defaultValue(columnName)))
        # a short saved list takes the holes it lacks from the defaults
        columnValues += self.defaultValue(columnName)[len(columnValues):row + 1]
        # the C++ inserted here, pushing every later hole down one
        columnValues[row] = toDouble(self.course.item(row, column).text())
        self.options[columnName] = columnValues
        self.optionsChanged.emit(self.options)
