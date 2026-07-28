from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QToolButton, QVBoxLayout, QWidget

_DEFAULT_MAX_CONTENT_HEIGHT = 280


class XkorCollapsibleSection(QWidget):
    """A disclosure-triangle header that shows/hides a content widget below
    it. Paradigm options widgets use this to tuck everything except the
    home-advantage checkbox/magnitude — formula constants, style modifiers,
    display toggles — behind an 'Advanced options' twisty, collapsed by
    default, so the common case isn't a wall of spinboxes. The content is
    always wrapped in a height-capped scroll area so a paradigm with a long
    list of constants doesn't push the rest of the wizard page off-screen;
    a short list simply never needs to scroll."""

    def __init__(self, title="Advanced options", parent=None,
                 maxContentHeight=_DEFAULT_MAX_CONTENT_HEIGHT):
        super().__init__(parent)
        self._maxContentHeight = maxContentHeight

        self.toggleButton = QToolButton()
        self.toggleButton.setText(title)
        self.toggleButton.setCheckable(True)
        self.toggleButton.setChecked(False)
        self.toggleButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggleButton.setArrowType(Qt.RightArrow)
        self.toggleButton.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.toggleButton.clicked.connect(self._onToggled)

        self.content = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggleButton)
        self._layout = layout

    def setContent(self, widget):
        """Install the widget shown/hidden by the twisty. Call once."""
        scrollArea = QScrollArea()
        scrollArea.setWidget(widget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setFrameShape(QFrame.NoFrame)
        scrollArea.setMaximumHeight(self._maxContentHeight)
        scrollArea.setVisible(self.toggleButton.isChecked())

        self._layout.addWidget(scrollArea)
        self.content = scrollArea

    def _onToggled(self, checked):
        self.toggleButton.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        if self.content is not None:
            self.content.setVisible(checked)
