"""A dropdown arrow on the selected row of a list whose editor is a combo box.

Nothing about these rows says they hold a choice rather than free text, so the
only way to find out was to double click one. Marking the selected row keeps
the hint to where the user is already looking, rather than putting an arrow on
every row and turning the list into a wall of chevrons.
"""

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QStyle, QStyleOption, QStyleOptionViewItem

INDICATOR_WIDTH = 14
ARROW_MAX = 9  # the glyph is a hint, not a control, so it never grows with the row
ARROW_MIN = 5


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
        # PE_IndicatorArrowDown fills whatever rect it is given, so give it a
        # small centred one rather than the whole row height. Row height
        # varies with the user's font, so leave a margin around it but never
        # let it grow past ARROW_MAX.
        size = max(ARROW_MIN, min(ARROW_MAX, strip.height() - 6))
        glyph = QRect(0, 0, size, size)
        glyph.moveCenter(strip.center())
        arrow = QStyleOption()
        arrow.rect = glyph
        arrow.state = option.state
        arrow.palette = option.palette
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorArrowDown, arrow, painter,
                            option.widget)
        painter.restore()
