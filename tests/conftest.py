import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensureQtPluginPath():
    # PySide6 normally registers its bundled Qt plugin directory from its
    # __init__.py. Some installs (e.g. a PySide6 dropped into site-packages
    # without an __init__.py, so Python treats it as a namespace package)
    # never run that, and every test that constructs a QApplication then
    # hard-aborts with "could not find the Qt platform plugin" -- a fatal
    # abort, not a catchable failure. Point Qt at the plugins ourselves.
    if os.environ.get("QT_PLUGIN_PATH"):
        return
    spec = importlib.util.find_spec("PySide6")
    if spec is None:
        return
    for root in list(spec.submodule_search_locations or []):
        plugins = os.path.join(root, "Qt", "plugins")
        if os.path.isdir(os.path.join(plugins, "platforms")):
            os.environ["QT_PLUGIN_PATH"] = plugins
            return


_ensureQtPluginPath()


import pytest


@pytest.fixture(scope="session")
def qapp():
    """One application object for every widget test in the session.

    An XkorApplication rather than a bare QApplication: it is what registers
    the "sports:" search path, and only one QApplication may exist per
    process. Building a plain one here left whichever test ran first to
    decide whether sports could be looked up at all.
    """
    from PySide6.QtWidgets import QApplication

    from xkoranate.application import XkorApplication

    app = QApplication.instance()
    if app is None:
        app = XkorApplication([])
    if isinstance(app, XkorApplication):
        app.refreshSearchPaths()
    return app
