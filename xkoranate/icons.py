"""Icon loader. Replaces the Qt resource file icons.qrc: icon("document-new").

Toolbar/action glyphs are served from the Material Design Icons font via
qtawesome, so the whole app gets a modern, theme-consistent icon set from the
single set of call sites that already use icon(<key>). Brand/raster images that
are not glyphs (the application icon) fall back to the bundled PNGs.

Glyphs are tinted with theme.ink(), which differs between light and dark mode.
QIcon objects don't repaint themselves when that changes, so actions created
via icon_action() are tracked in a small registry and re-issued a fresh icon
by refresh_icons(), which runs whenever theme.signal.changed fires.
"""

import os

from PySide6.QtGui import QIcon

from .paths import iconsDir
from . import theme

# map the app's icon keys to Material Design Icon (mdi6) glyph names
_MDI = {
    "document-new": "mdi6.file-plus-outline",
    "document-open": "mdi6.folder-open-outline",
    "document-save": "mdi6.content-save-outline",
    "document-save-as": "mdi6.content-save-edit-outline",
    "document-import": "mdi6.import",
    "document-export": "mdi6.export",
    "table-generator": "mdi6.table",
    "table-generator-refresh": "mdi6.table-refresh",
    "add": "mdi6.plus",
    "remove": "mdi6.minus",
    "roll": "mdi6.dice-multiple-outline",
    "add-participant": "mdi6.account-plus-outline",
    "add-all-participants": "mdi6.account-multiple-plus-outline",
    "schedule": "mdi6.calendar-month-outline",
    "odds": "mdi6.percent-outline",
    "seed": "mdi6.sort-numeric-ascending",
    "spread-seeds": "mdi6.arrow-expand-horizontal",
}

# (action, glyph key) pairs created via icon_action(), so refresh_icons() can
# re-tint them after a light/dark toggle
_tinted_actions = []


def _png(name):
    return QIcon(os.path.join(iconsDir(), name + ".png"))


def icon(name):
    glyph = _MDI.get(name)
    if glyph is not None:
        try:
            import qtawesome
            return qtawesome.icon(glyph, color=theme.ink())
        except Exception:
            pass  # fall back to a bundled PNG if qtawesome is unavailable
    return _png(name)


def icon_action(name, text, parent):
    """Build a QAction whose icon tracks the current theme. Use this instead
    of QAction(icon(name), text, parent) for any action that should re-tint
    when the user flips light/dark mode."""
    from PySide6.QtGui import QAction

    action = QAction(icon(name), text, parent)
    _tinted_actions.append((action, name))
    return action


def refresh_icons():
    global _tinted_actions
    alive = []
    for action, name in _tinted_actions:
        try:
            action.setIcon(icon(name))
        except RuntimeError:
            continue  # underlying C++ QAction was deleted
        alive.append((action, name))
    _tinted_actions = alive


theme.signal.changed.connect(refresh_icons)
