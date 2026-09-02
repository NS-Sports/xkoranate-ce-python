"""A dropdown arrow on the selected row of a list whose editor is a combo box.

Nothing about these rows says they hold a choice rather than free text, so the
only way to find out was to double click one. Marking the selected row keeps
the hint to where the user is already looking, rather than putting an arrow on
every row and turning the list into a wall of chevrons.
"""

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QStyle, QStyleOption, QStyleOptionViewItem

INDICATOR_WIDTH = 16


class XkorComboIndicatorMixin:
    """Draws the arrow. Mix in before the delegate's own base class."""

    def usesComboEditor(self, index):
        """Whether this cell's editor is a combo box. Override as needed."""
        return True

    def paint(self, painter, option, index):
        if not (option.state & QStyle.StateFlag.State_Selected) or not self.usesComboEditor(index):
            super().paint(painter, option, index)
            return

        # keep the text clear of the arrow, so a long name elides rather than
        # running underneath it
        text = QStyleOptionViewItem(option)
        text.rect = option.rect.adjusted(0, 0, -INDICATOR_WIDTH, 0)
        super().paint(painter, text, index)

        strip = QRect(option.rect.right() - INDICATOR_WIDTH, option.rect.top(),
                      INDICATOR_WIDTH, option.rect.height())
        painter.save()
        painter.fillRect(strip, option.palette.highlight())
        arrow = QStyleOption()
        arrow.rect = strip
        arrow.state = option.state
        arrow.palette = option.palette
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorArrowDown, arrow, painter,
                            option.widget)
        painter.restore()
