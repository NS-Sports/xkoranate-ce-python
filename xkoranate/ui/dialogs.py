"""Shared QMessageBox construction. Several screens pop an "xkoranate"-branded
confirmation dialog (unsaved changes, destructive re-scorination, etc.); this
gives them one place to build it consistently instead of each hand-rolling
the brand icon pixmap and modality flags."""

import os

from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QMessageBox,
                               QPlainTextEdit, QStyle, QVBoxLayout)

from .. import theme
from ..paths import iconsDir
from .fonts import monospace_font


def resolved_search_path(prefix):
    """Resolve a QDir.setSearchPaths() prefix (e.g. "events") to a real
    absolute directory, falling back to the home directory.

    QFileDialog's own model resolves a "prefix:/" search-path string fine,
    but the native platform dialog (the default on Windows) is handed that
    string unresolved as its starting folder — Windows then tries to open
    "prefix:" as if it were a URL scheme and pops "you can't open this
    location using this program." Passing a real path avoids that lookup
    entirely."""
    d = QDir(f"{prefix}:/")
    return d.absolutePath() if d.exists() else QDir.homePath()


def brand_pixmap(widget, size=None):
    """The xkoranate icon, scaled for use as a QMessageBox.setIconPixmap()."""
    iconSize = size or widget.style().pixelMetric(QStyle.PM_MessageBoxIconSize)
    return (QPixmap(os.path.join(iconsDir(), "xkoranate.png"))
            .scaled(iconSize, iconSize, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))


def message_box(parent, text, buttons, informativeText="", icon=QMessageBox.NoIcon,
                defaultButton=None, escapeButton=None, destructiveButton=None):
    """Build (but don't exec()) an "xkoranate"-branded QMessageBox. Passing
    icon=QMessageBox.NoIcon (the default) uses the brand icon in place of a
    generic system one; pass e.g. QMessageBox.Warning to get that instead.

    destructiveButton names the button (e.g. QMessageBox.Discard, or Ok when
    "Ok" means "yes, lose my data") that should read as a warning rather than
    the app's positive accent colour — so "discard my changes" never looks
    like the safe, recommended choice. Cancel/Close, if present, are recoloured
    to a neutral grey for the same reason: backing out isn't the accent action
    either."""
    box = QMessageBox(icon, "xkoranate", text, buttons, parent)
    if icon == QMessageBox.NoIcon:
        box.setIconPixmap(brand_pixmap(parent))
    if informativeText:
        box.setInformativeText(informativeText)
    if defaultButton is not None:
        box.setDefaultButton(defaultButton)
    if escapeButton is not None:
        box.setEscapeButton(escapeButton)
    box.setWindowModality(Qt.WindowModal)

    dangerBtn = box.button(destructiveButton) if destructiveButton is not None else None
    if dangerBtn is not None:
        dangerBtn.setStyleSheet(
            "QPushButton { color: %s; border-color: %s; }" % (theme.danger(), theme.danger()))

    for role in (QMessageBox.Cancel, QMessageBox.Close):
        neutralBtn = box.button(role)
        if neutralBtn is not None and neutralBtn is not dangerBtn:
            # qdarktheme fills whichever button is QMessageBox.setDefaultButton()
            # with the accent colour (its QPushButton:default rule) — override
            # background/border too, not just text colour, so a
            # defaultButton=Cancel/Close never reads as the accent action
            neutralBtn.setStyleSheet(
                "QPushButton { background: transparent; border: 1px solid %s; color: %s; }"
                % (theme.muted(), theme.muted()))

    return box


def text_preview_dialog(parent, title, text):
    """Show read-only text (a schedule, odds, etc.) in its own modal dialog.
    Never reuse a results/output text widget for this — overwriting it
    leaves no way back to whatever it was showing before short of navigating
    away and back."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.resize(560, 420)

    preview = QPlainTextEdit(text)
    preview.setReadOnly(True)
    preview.setFont(monospace_font())

    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)

    layout = QVBoxLayout(dialog)
    layout.addWidget(preview, 1)
    layout.addWidget(buttons)

    dialog.exec()
