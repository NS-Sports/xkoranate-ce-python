"""Opens the online user guide when the user asks for help.

The guide is the GitHub Pages site built from docs/. Each window gets a
"help" action bound to the platform's help key (F1 on Windows and Linux,
Cmd+? on macOS) plus a plain F1 everywhere, since that is the key most
people try first. A window can point at the guide page that covers it.
"""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence

MANUAL_URL = "https://ns-sports.github.io/xkoranate-ce-python/"


def manual_url(page=""):
    """The guide's address, or one page of it ("table-generator/")."""
    return MANUAL_URL + page


def open_manual(page=""):
    return QDesktopServices.openUrl(QUrl(manual_url(page)))


def help_shortcuts():
    """The platform's help key, and F1 if the platform uses something else."""
    keys = list(QKeySequence.keyBindings(QKeySequence.HelpContents))
    f1 = QKeySequence("F1")
    if f1 not in keys:
        keys.append(f1)
    return keys


def help_action(parent, page="", text="xkoranate manual"):
    action = QAction(text, parent)
    action.setShortcuts(help_shortcuts())
    action.setToolTip("Open the user guide in your web browser")
    action.triggered.connect(lambda: open_manual(page))
    return action
