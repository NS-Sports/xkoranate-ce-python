from PySide6.QtWidgets import QGridLayout, QLabel


def pointsRowLayout(win, draw, loss):
    """Win, draw and loss points boxes in one row, labelled between them."""
    layout = QGridLayout()
    layout.addWidget(win, 0, 0)
    layout.addWidget(QLabel("Draw:"), 0, 1)
    layout.addWidget(draw, 0, 2)
    layout.addWidget(QLabel("Loss:"), 0, 3)
    layout.addWidget(loss, 0, 4)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(1, 0)  # don't stretch the labels
    layout.setColumnStretch(2, 1)
    layout.setColumnStretch(3, 0)  # don't stretch the labels
    layout.setColumnStretch(4, 1)
    return layout
