"""Regenerate the user guide's screenshots (docs/screenshots/guide-*.png).

    pixi run python tools/docs_screenshots.py

Builds a sample file, "My Tournament": a football Group Stage, a Knockout
and a 100 m final. It then opens it in the real app, walks each screen and
saves a picture of it. The app's windows flash up on screen while it runs.

Your own xkoranate settings (theme, remembered folders) are put back the
way they were when it finishes.
"""

import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QAbstractItemView, QApplication

from xkoranate import theme
from xkoranate.application import XkorApplication
from xkoranate.athlete import XkorAthlete
from xkoranate.event import XkorEvent
from xkoranate.group import XkorGroup
from xkoranate.paths import appSettings
from xkoranate.rplist import XkorRPList
from xkoranate.signuplist import XkorSignupList
from xkoranate.xml.xmlindex import XkorXmlIndex
from xkoranate.xml.xmlsportreader import XkorXmlSportReader
from xkoranate.xml.xmlwriter import XkorXmlWriter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "screenshots")
WINDOW = (1100, 720)

FOOTBALL = "Association football—SQIS formula"
SPRINT = "Athletics—Women’s 00100 m—Round 4"  # the index key, not the label

# (nation, team code, skill)
NATIONS = [
    ("Aurelia", "AUR", 88),
    ("Bremmark", "BRE", 81),
    ("Castavia", "CAS", 76),
    ("Dornholt", "DOR", 70),
    ("Elsmere", "ELS", 64),
    ("Farrowland", "FAR", 58),
    ("Galtria", "GAL", 52),
    ("Hollisande", "HOL", 45),
]

SPRINTERS = [
    ("Mara Lindqvist", "AUR", 91),
    ("Tessa Okonjo", "CAS", 87),
    ("Ilse Varga", "BRE", 84),
    ("June Halloran", "ELS", 80),
    ("Priya Desmond", "GAL", 77),
    ("Ada Kowalczyk", "DOR", 73),
    ("Noor Abernathy", "HOL", 70),
    ("Ruth Calloway", "FAR", 66),
]


def signups(rows):
    sl = XkorSignupList()
    sl.setMinRank(0)
    sl.setMaxRank(100)
    for name, nation, skill in rows:
        a = XkorAthlete()
        a.name = name
        a.nation = nation
        a.skill = skill
        sl.addAthlete(a)
    return sl


def event(index, name, sportName, sl, competition, groups):
    sport = XkorXmlSportReader(index.lookup(sportName)).sport()
    ev = XkorEvent()
    ev.setName(name)
    ev.setSignupList(sl)
    ev.setSport(sport.name(), sport.paradigm())  # the label the sport list shows
    ev.setCompetition(competition)
    ids = {a.name: a.id for a in sl.athletes()}
    for groupName, members in groups:
        ev.addGroup(XkorGroup(groupName, [ids[m] for m in members]))
    return ev


def build_sample_file(path):
    index = XkorXmlIndex()
    index.traverse("sports:")

    # one event per stage, the way NS Sports runs a tournament: a group
    # stage of two groups, then a knockout for the top two of each
    teams = [(n, c, s) for n, c, s in NATIONS]
    names = [n for n, _, _ in NATIONS]
    league = event(index, "Group Stage", FOOTBALL, signups(teams),
                   "roundRobin", [("Group A", names[:4]), ("Group B", names[4:])])

    # group winners against the other group's runners-up
    order = ["Aurelia", "Farrowland", "Elsmere", "Bremmark"]
    cup = event(index, "Knockout", FOOTBALL, signups([t for t in teams if t[0] in order]),
                "singleElimination", [("Bracket", order)])

    sprint = event(index, "Women’s 100 m final", SPRINT, signups(SPRINTERS),
                   "standard", [("Final", [s[0] for s in SPRINTERS])])

    rp = XkorRPList()  # no roleplay bonuses: the guide doesn't cover them
    rp.setCompetitionName("My Tournament")

    XkorXmlWriter(path, rp, [(uuid.uuid4(), league), (uuid.uuid4(), cup), (uuid.uuid4(), sprint)])


class Shooter:
    def __init__(self, app):
        self.app = app
        self.win = app.mainWindow
        os.makedirs(OUT, exist_ok=True)

    def settle(self, rounds=8):
        for _ in range(rounds):
            QApplication.processEvents()

    def save(self, widget, name):
        # drop any hover highlight left by wherever the real mouse pointer
        # happens to be, so it can't pass for a selection
        for view in widget.findChildren(QAbstractItemView):
            QApplication.sendEvent(view.viewport(), QEvent(QEvent.Leave))
        self.settle()
        path = os.path.join(OUT, "guide-%s.png" % name)
        widget.grab().save(path)
        print("saved", os.path.relpath(path))

    def window(self, name):
        self.save(self.win, name)

    def modal(self, name, trigger):
        """Run something that opens a dialog, picture the dialog, close it."""
        def shoot():
            dialog = QApplication.activeModalWidget()
            if dialog is None:
                print("no dialog appeared for", name)
                return
            self.save(dialog, name)
            # a message box returns the button pressed; reject() alone
            # returns no button, which the app reads as "go ahead"
            escape = getattr(dialog, "escapeButton", lambda: None)()
            if escape is not None:
                escape.click()
            else:
                dialog.reject()
        QTimer.singleShot(600, shoot)
        trigger()

    def select_event(self, i):
        nw = self.app.cw.nw
        nw.treeWidget.setCurrentItem(nw.m_eventsItem.child(i), 0)
        self.settle()

    def centre_sport(self):
        """Scroll the sport list so the chosen sport is in view."""
        for view in self.app.cw.ee.sportSelector.findChildren(QAbstractItemView):
            selected = view.selectionModel().selectedIndexes() if view.selectionModel() else []
            if selected:
                view.scrollTo(selected[0], QAbstractItemView.PositionAtCenter)
        self.settle()

    def step(self, n):
        """Go to wizard step n (1-5) of the selected event."""
        ee = self.app.cw.ee
        while ee.stack.currentIndex() > n - 1:
            ee.goPrev()
        while ee.stack.currentIndex() < n - 1:
            ee.goNext()
        self.settle()


def run(shots, workdir):
    app = shots.app
    cw = app.cw
    ee = cw.ee

    # a brand-new window, before anything is opened
    shots.window("01-first-launch")

    sample = os.path.join(workdir, "my-tournament.xml")
    build_sample_file(sample)
    cw.openFile(sample)
    shots.settle()
    cw.nw.treeWidget.expandAll()


    # group stage: every step of the wizard
    shots.select_event(0)
    for n, name in [(1, "03-step-sport"), (2, "04-step-signups"),
                    (3, "05-step-competition"), (4, "06-step-groups")]:
        shots.step(n)
        if n == 1:
            shots.centre_sport()
        shots.window(name)

    shots.modal("07-schedule", ee.viewSchedule)

    shots.step(5)
    sw = ee.scorinateWidget
    shots.window("08-step-scorinate-empty")
    days = sw.matchday.count()
    for md in range(days):
        sw.matchday.setCurrentIndex(md)
        sw.scorinateMatchday(md)
    sw.matchday.setCurrentIndex(0)
    shots.window("09-step-scorinate-results")

    sw.bbcodeCheckBox.setChecked(True)
    sw.updateResults(0)
    shots.window("10-scorinate-bbcode")
    sw.bbcodeCheckBox.setChecked(False)
    sw.updateResults(0)

    sw.matchday.setCurrentIndex(days - 1)
    if sw.oddsAction.isEnabled():
        shots.modal("11-odds", sw.viewOdds)
    sw.matchday.setCurrentIndex(0)

    # what a re-scorinate warns you about
    shots.modal("12-regenerate-warning", sw.scorinate)

    # the table generator makes one table, so feed it Group A's matches only
    groupA = ["(%s)" % c for _, c, _ in NATIONS[:4]]
    lines = ["Group A"]
    for md in range(days):
        lines += [line for line in sw.c.results(md).splitlines()
                  if any(code in line for code in groupA)]
    results_file = os.path.join(workdir, "group-a-results.txt")
    with open(results_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 100 m final: a race, every step
    shots.select_event(2)
    for n, name in [(1, "20-race-sport"), (2, "21-race-signups"),
                    (3, "22-race-competition"), (4, "23-race-groups")]:
        shots.step(n)
        if n == 1:
            shots.centre_sport()
        shots.window(name)
    shots.step(5)
    sw.scorinateMatchday(0)
    shots.window("16-race-results")

    # knockout: the bracket and the semi-finals
    shots.select_event(1)
    shots.step(4)
    shots.window("13-step-bracket")
    shots.modal("14-bracket-schedule", ee.viewSchedule)
    shots.step(5)
    sw.scorinateMatchday(0)
    sw.matchday.setCurrentIndex(0)
    shots.window("15-knockout-results")

    # the "save your changes?" question
    shots.modal("17-unsaved-changes", cw.showUnsavedDialog)

    # table generator, fed the group's results
    app.tableGenerator()
    tg = app.tg
    tg.resize(*WINDOW)
    tg.show()
    shots.settle()
    tg.generator.importResults(results_file)
    tg.generator.generateTable()
    shots.save(tg, "18-table-generator")
    tg.generator.setFileModified(False) if hasattr(tg.generator, "setFileModified") else None
    tg.close()

    # dark mode, on the scorinate screen
    shots.select_event(0)
    shots.step(5)
    theme.set_mode(app, "dark")
    shots.settle()
    shots.window("19-dark-mode")


def main():
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # only the keys the app writes; anything else in the store is left alone
    keys = ["themeMode", "eventDirectory", "resultExportDirectory",
            "resultImportDirectory", "signupListDirectory", "tableDirectory"]
    settings = appSettings()
    saved = {k: settings.value(k) for k in keys if settings.contains(k)}
    settings.setValue("themeMode", "light")
    try:
        app = XkorApplication(sys.argv)
        app.loadSports()
        app.mainWindow.resize(*WINDOW)
        app.mainWindow.show()
        shots = Shooter(app)
        shots.settle(20)
        with tempfile.TemporaryDirectory() as workdir:
            run(shots, workdir)
        # nothing in the sample file is worth keeping
        app.cw.setModified(False)
        if app.tg is not None:
            app.tg.generator.close = lambda: True
        app.closeAllWindows()
    finally:
        for k in keys:
            if k in saved:
                settings.setValue(k, saved[k])
            else:
                settings.remove(k)
        settings.sync()


if __name__ == "__main__":
    main()
