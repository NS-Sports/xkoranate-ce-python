from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QStyle, QToolBar


def small_icon_toolbar(widget, actions, vertical=False):
    """A tool bar holding actions at widget's small icon size. None in
    actions adds a separator."""
    toolBar = QToolBar()
    small = widget.style().pixelMetric(QStyle.PM_SmallIconSize)
    toolBar.setIconSize(QSize(small, small))
    if vertical:
        toolBar.setOrientation(Qt.Vertical)
    for i in actions:
        if i is None:
            toolBar.addSeparator()
        else:
            toolBar.addAction(i)
    return toolBar
