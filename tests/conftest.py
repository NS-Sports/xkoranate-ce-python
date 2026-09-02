import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import pytest


@pytest.fixture(scope="session")
def qapp():
    """One QApplication for every widget test in the session."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
