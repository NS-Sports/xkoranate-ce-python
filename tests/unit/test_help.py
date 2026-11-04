"""The help key opens the online user guide."""

from PySide6.QtGui import QDesktopServices, QKeySequence

from xkoranate import help as xhelp


def _capture_urls(monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    return opened


def test_f1_is_always_a_help_key(qapp):
    keys = xhelp.help_shortcuts()
    assert QKeySequence("F1") in keys
    for key in QKeySequence.keyBindings(QKeySequence.HelpContents):
        assert key in keys
    assert len(keys) == len(set(k.toString() for k in keys))


def test_main_window_help_opens_the_guide(qapp, monkeypatch):
    opened = _capture_urls(monkeypatch)
    qapp.helpAction.trigger()
    assert opened == [xhelp.MANUAL_URL]
    assert QKeySequence("F1") in qapp.helpAction.shortcuts()


def test_main_window_has_a_help_menu(qapp):
    titles = [a.text() for a in qapp.mainWindow.menuBar().actions()]
    assert "&Help" in titles


def test_table_generator_help_opens_its_page(qapp, monkeypatch):
    from xkoranate.tablegenerator.tablegeneratorwindow import XkorTableGeneratorWindow

    opened = _capture_urls(monkeypatch)
    window = XkorTableGeneratorWindow()
    try:
        assert window.helpAction in window.actions()
        window.helpAction.trigger()
        assert opened == [xhelp.MANUAL_URL + "table-generator/"]
    finally:
        window.deleteLater()
