"""Central place for the application's visual theme.

A flat, modern theme is applied via PyQtDarkTheme (qdarktheme), in one of
three modes — light, dark, or true dark (an OLED-friendly, pure-black variant
of dark) — with a single fixed accent colour running through all of them.
Other modules (icons.py, ui/typography.py, eventeditor.py's wizard
breadcrumb) read ACCENT / ink() / muted() from here rather than hardcoding
colours, and listen on `signal.changed` so everything re-tints together when
the mode is switched at runtime.
"""

from PySide6.QtCore import QObject, Signal

from .paths import appSettings

# fixed in all modes — deliberately not qdarktheme's default blue. Used for
# fills/indicators (buttons, toggle switch, radio/checkbox) where contrast is
# checked against an adjacent colour, not for literal text on a page.
ACCENT = "#8EC23A" # Mertagnian Green ;)

MODES = ["light", "dark", "oled"]
MODE_LABELS = {"light": "Light", "dark": "Dark", "oled": "True Dark (OLED)"}

# "oled" is dark's text/glyph colours over a pure-black background, so it
# shares dark's entries in the dicts below.
_INK = {"light": "#37474f", "dark": "#eceff1", "oled": "#eceff1"}     # icon / glyph colour
_MUTED = {"light": "#78909c", "dark": "#90a4ae", "oled": "#90a4ae"}   # secondary/de-emphasised text

# ACCENT itself is ~2.1:1 against white — well under WCAG AA's 4.5:1 for text.
# Use a darkened/lightened same-hue variant wherever the accent colours a
# text glyph directly (e.g. the wizard breadcrumb) instead of filling a shape.
_ACCENT_TEXT = {"light": "#4E6B20", "dark": ACCENT, "oled": ACCENT}

# for destructive actions (Discard, "lose your changes" confirmations) — kept
# out of the main ACCENT so a "yes, delete this" button never reads as the
# safe/positive choice. Also mode-tuned for contrast, same reasoning as above.
_DANGER = {"light": "#C13333", "dark": "#E06C6C", "oled": "#E06C6C"}

_SETTINGS_KEY = "themeMode"
DEFAULT_MODE = "light"


class _ThemeSignal(QObject):
    changed = Signal()


# a single shared instance other modules can connect to
signal = _ThemeSignal()


def mode():
    """The active theme mode: "light", "dark", or "oled"."""
    return appSettings().value(_SETTINGS_KEY, DEFAULT_MODE)


def is_dark():
    """True for "dark" and "oled" — modes that share dark's icon/text colours."""
    return mode() in ("dark", "oled")


def ink():
    return _INK.get(mode(), _INK[DEFAULT_MODE])


def muted():
    return _MUTED.get(mode(), _MUTED[DEFAULT_MODE])


def accent_text():
    """ACCENT, adjusted for use as literal text/glyph colour on a page
    background rather than as a filled shape."""
    return _ACCENT_TEXT.get(mode(), _ACCENT_TEXT[DEFAULT_MODE])


def danger():
    return _DANGER.get(mode(), _DANGER[DEFAULT_MODE])


def primary_button_qss():
    """qdarktheme has no built-in "primary/filled" button variant, and its own
    default-button styling otherwise wins over an app-wide selector — so the
    wizard's Continue button gets this applied directly as its own
    widget.setStyleSheet(), which always outranks the application stylesheet."""
    return (
        "QPushButton { background-color: %s; color: #ffffff; border: none; } "
        "QPushButton:disabled { background-color: %s; color: #ffffff; }"
    ) % (ACCENT, muted())


def apply(app):
    """Apply the current theme to the QApplication. Safe no-op if the
    theming library is unavailable (the app still runs with the native
    style)."""
    try:
        import qdarktheme
    except Exception:
        return
    currentMode = mode()
    customColors = {"primary": ACCENT}
    # qdarktheme has no OLED mode of its own — "oled" is dark's palette with
    # the background forced to pure black instead of its usual dark grey.
    qdarkthemeMode = "dark" if currentMode == "oled" else currentMode
    if currentMode == "oled":
        customColors["background"] = "#000000"
    qdarktheme.setup_theme(qdarkthemeMode, custom_colors=customColors)


def set_mode(app, newMode):
    """Switch between "light", "dark", and "oled", persist the choice,
    re-apply the stylesheet, and notify listeners (icons, breadcrumb, etc.)
    to re-tint."""
    if newMode == mode():
        return
    appSettings().setValue(_SETTINGS_KEY, newMode)
    apply(app)
    signal.changed.emit()
