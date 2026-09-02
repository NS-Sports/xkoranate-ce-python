# xkoranate-CE — Improvement roadmap

This document captures two planning deliverables produced alongside the UI
refresh: (1) a prioritized triage of the upstream GitHub issues, and (2) a
feasibility assessment for Windows support. Neither is implemented yet — this is
the plan for tackling them.

Issue numbers refer to <https://github.com/NS-Sports/Xkoranate-CE/issues>.

---

## 1. Issue triage — prioritized

Two issues are already resolved or moot:

- **#19 Mac64 support** — *solved* by the Python/Qt6 port (runs natively on
  64-bit macOS).
- **#10 New basketball formulas** — already **closed** upstream.

### Tier 1 — Easy wins (small, localized, low risk)

| Issue | Type | Where | Fix |
|---|---|---|---|
| **#3** Rank sorts alphabetically, not numerically | bug | `signuplisteditor/athletewidget.py`, `abstractathletewidget.py` | The athlete tree uses `setSortingEnabled(True)`; Qt compares the column as text. Store the numeric value in a sort role / subclass `QTreeWidgetItem.__lt__` to compare numerically. ~1–2 hrs. |
| **#36** BBCode `[pre]`/`[b]` output | feature | `paradigms/abstractparadigm.py` (`output()`), `eventeditor/scorinatewidget.py` | Output is assembled as plain text. Add a checkbox that wraps results in `[pre]…[/pre]` (optionally bold match winners) at the display/export boundary. No core-logic change. ~2–3 hrs. |
| **#2** Style mods missing from CSV/TXT import | bug | `signuplisteditor/athletewidget.py:99-108` | Import hard-codes `len(l) == 3` and ignores extra columns; `initItem` already accepts a `properties` dict. Parse extra fields (e.g. `style`) into it. ~2 hrs. |
| **#8** Adjustable home-field advantage | feature | `paradigms/options/footba11erparadigmoptions.py`; value already read in `paradigms/footba11erparadigm.py` | The magnitude already exists as a sport-file paradigm option; only the on/off checkbox is user-facing. Expose the magnitude as a `QDoubleSpinBox`. ~2–3 hrs. *(Do before #9.)* |

### Tier 2 — Medium (more logic; needs care + tests)

| Issue | Type | Where | Fix |
|---|---|---|---|
| **#1** Penalty-shootout results not counted in standings | bug | `competitions/roundrobincompetition.py` (~line 246), `tablegenerator/tablerow.py` | Shootout tiebreaker scores are explicitly excluded from the table match, so a shootout is recorded as a draw. When draws are disallowed and a shootout decided the match, record W/L for the correct side and award win/loss points. Must not regress the draws-allowed path. ~1 day. |
| **#7** Table ignores prior matchdays when tiebreakers change | bug | `competitions/roundrobincompetition.py` (scorinate/revert), `tablegenerator/table.py` | Table is rebuilt from the current matchday's stored data, not re-accumulated from all played matchdays. Rebuild standings from the full set of played matches each time, applying the current tiebreakers. ~1 day. |
| **#9** Home advantage applied incorrectly | bug | `paradigms/footba11erparadigm.py` / `nsfsparadigm.py` (`generateFTScore`/`generateScore`) | Reproduce against the linked forum report first, then correct the math. Mostly investigation. ~1 day. Pairs with #8. |
| **#34** Automatic schedule output | feature | `competitions/roundrobincompetition.py` (`generateFixtures()`) | Fixtures are already computed; add a button to format/export the full matchday schedule. ~½ day. |
| **#33** Odds calculator | feature | `competitions/roundrobincompetition.py`, `athlete.py`, paradigm skill-ratio math | Skills and skill-ratio math exist; add a small UI to show per-match win % from fixtures + skills. Paradigm-specific — start with football/H2H. ~1–2 days. |

### Tier 3 — Large features / new subsystems (separate projects)

Tracked as issues in this repo (each links back to the original upstream
report):

- [#23](https://github.com/NS-Sports/xkoranate-ce-python/issues/23) New paradigms (boxing, MMA, quidditch, 3×3; Baseinator-style additive mods) — multiple new scoring engines. (upstream #11)
- [#24](https://github.com/NS-Sports/xkoranate-ce-python/issues/24) Inter-conference play — new competition type + options file. (upstream #18)
- [#25](https://github.com/NS-Sports/xkoranate-ce-python/issues/25) Sailing multi-round Olympic automation — domain-heavy. (upstream #5)
- [#26](https://github.com/NS-Sports/xkoranate-ce-python/issues/26) Auto-racing multiclass / timed races — new options + paradigm work. (upstream #37)
- [#27](https://github.com/NS-Sports/xkoranate-ce-python/issues/27) In-app formula/XML editor for sports — substantial new editor subsystem. (upstream #35)
- [#28](https://github.com/NS-Sports/xkoranate-ce-python/issues/28) Document paradigms, paradigm options, and the sport-file XML format. (upstream #4)

**Suggested implementation order:** #3 → #36 → #2 → #8 → #9 → #1 → #7 → #34 →
#33, then Tier 3 case-by-case.

---

## 2. Windows support — feasibility

**Status: implemented** — `xkoranate.spec` now branches on `sys.platform`
(macOS `.app` bundle vs. Windows/Linux onedir build with a `.ico` icon), CI
builds and verifies all three platforms on every push, and
`.github/workflows/release.yml` publishes the built artifacts to a draft
GitHub release on tag push.

**Verdict: highly feasible. The core application needs essentially zero code
changes.** The Python port uses Qt's cross-platform APIs throughout
(`QSettings`, `QDir.homePath`, `QFileDialog`, `os.path.join`/`normpath`, font
*hints* not hardcoded families). `paths.py` already falls back to
`sys._MEIPASS`, which is exactly the Windows PyInstaller layout. The theme
(qt-material) and icons (qtawesome) are cross-platform.

### Concrete tasks (all small)

1. **macOS-only call** — `tablegenerator/tablegeneratorwindow.py`'s
   `setUnifiedTitleAndToolBarOnMac()` is now guarded with `hasattr(...)` (fixed
   during the UI work), so it no longer raises on Windows. ✓
2. **PyInstaller spec** — `xkoranate.spec` is macOS-only (`BUNDLE` + `.icns` +
   `info_plist`). Add a Windows path: drop `BUNDLE`, keep `EXE` + `COLLECT`, set
   a `.ico` icon, `console=False`. Output: `dist/xkoranate/xkoranate.exe`.
   Easiest: branch the spec on `sys.platform`, or add a separate
   `xkoranate_win.spec`. The `collect_all("qt_material")` /
   `collect_all("qtawesome")` lines already in the spec are needed on Windows too
   (already present).
3. **Icon format** — need a `.ico`. The original C++ repo already ships one at
   `src/icons/xkoranate.ico`; copy it to `xkoranate/icons/`.
4. **Build script** — `build_app.sh` is a shell script; add a `build_app.bat` or
   a small cross-platform Python build entry.

**Estimated effort:** ~2–3 hours plus a test pass on a Windows machine/VM.
`QSettings` will transparently use the Windows registry; no code change needed.
