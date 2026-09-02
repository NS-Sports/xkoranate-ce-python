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
