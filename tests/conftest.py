import functools
import importlib.util
import os
import subprocess
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


@functools.lru_cache(maxsize=None)
def _canCreateQApplication():
    """Whether a QApplication can be constructed here at all.

    Qt aborts the process outright when no platform plugin will load, which
    would take the whole test session down with it rather than failing one
    test — and an installation can advertise a plugin directory holding an
    offscreen plugin it still can't load. So find out in a throwaway
    subprocess, where an abort costs nothing."""
    return subprocess.run(
        [sys.executable, "-c",
         "from PySide6.QtWidgets import QApplication; QApplication([])"],
        capture_output=True).returncode == 0


@pytest.fixture(scope="session")
def qapp():
    """One application object for every widget test in the session.

    An XkorApplication rather than a bare QApplication: it is what registers
    the "sports:" search path and builds the main window, and only one
    QApplication may exist per process. Test files that built a plain one
    of their own left whichever ran first to decide what every later test
    got.
    """
    from xkoranate.application import XkorApplication

    app = XkorApplication.instance()
    if app is None:
        if not _canCreateQApplication():
            pytest.skip("no usable Qt platform plugin for this interpreter")
        app = XkorApplication([])
    app.refreshSearchPaths()
    return app


@pytest.fixture(scope="session")
def sport_index(qapp):
    """Every sport file, found through the "sports:" search path that the
    application registers."""
    from xkoranate.xml.xmlindex import XkorXmlIndex

    index = XkorXmlIndex()
    index.traverse("sports:")
    return index


@pytest.fixture
def rng():
    """A fresh seeded generator per test.

    Module scope shared one stream across the whole file, so how far into it
    any given test started depended on which tests ran before it. Running a
    subset, or inserting a test above an existing one, silently changed every
    later test's numbers — fine for today's structural assertions, a
    heisenbug for the first outcome-sensitive one.
    """
    from xkoranate.rng import Mt19937

    return Mt19937(2026)


@pytest.fixture
def tournament(sport_index, rng):
    """tournament(name, **overrides) -> (event, sport), one of
    builders.TOURNAMENTS built fresh, drawing from this test's rng unless
    given another."""
    import builders

    def build(name, rng=rng, **overrides):
        return builders.tournament(name, sport_index, rng, **overrides)

    return build
