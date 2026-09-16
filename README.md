# xkoranate-CE (Python port)

A faithful Python/PySide6 port of [xkoranate-CE](https://github.com/NS-Sports/Xkoranate-CE)
(xkoranate **C**ommunity **E**dition), the sports "scorinator" used by NS Sports,
the sports roleplay forum for NationStates. Originally written in Qt4/C++ by
Commerce Heights/ThirdGeek; this port preserves the original program's behavior —
scorination math, competition formats, file formats and UI — while running on
current macOS, Windows, and Linux via Python and Qt 6.

It simulates results for one hundred–plus disciplines across sixty-plus sports:
mass starts, head-to-head matches, round robins, knockout brackets, multi-run
events, shooting and archery formats, and includes the league table generator.

The interface has a modern, light Material-style theme (via `qt-material`) with
Material Design Icons (`qtawesome`); the underlying behaviour is unchanged.

**Using the app?** See the [user guide](https://ns-sports.github.io/xkoranate-ce-python/)
for downloads, a tour of the event editor, and the table generator. The rest
of this README covers building and developing xkoranate itself.

## Running from source

Dev environments are managed with [pixi](https://pixi.sh) — it resolves
PySide6/Qt as matched conda-forge binaries and locks the whole environment
(`pixi.lock`), which avoids the class of bug where a global Python
install's Qt bindings and native libraries drift out of sync.

```sh
pixi run run            # launch the app from source
pixi run test            # unit tests
pixi run test-integration  # integration tests (boots the app headless)
pixi run test-all        # both
```

`pixi shell` drops you into the environment directly if you'd rather run
commands (e.g. `python -m xkoranate`) without the `pixi run` prefix.

## Building the app

The same PyInstaller spec (`xkoranate.spec`) produces a native build on
macOS, Windows, and Linux — it branches on the host platform automatically.
This uses a plain venv rather than pixi, since PyInstaller freezes whatever
CPython build it's run with into the app bundle, and that needs to be a
standard CPython distribution rather than conda-forge's Python.

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/pip install -e . pyinstaller
./build_app.sh
# macOS -> dist/xkoranate.app
# Linux -> dist/xkoranate/xkoranate
```

Windows:

```bat
python -m venv .venv
.venv\Scripts\pip install -e . pyinstaller
build_app.bat
:: -> dist\xkoranate\xkoranate.exe
```

The build bundles the `sports/` definitions directory alongside the app
(`Contents/Resources/sports/` on macOS, `sports/` next to the exe/binary on
Windows/Linux). Sport parameter files are plain XML and remain user-editable
there. The PyInstaller spec also bundles the `qdarktheme` and `qtawesome`
data files so the theme and icons work in the frozen app.

On Linux, PyInstaller only bundles a shared library into `dist/` if it can
resolve it (via `ldd`) on the *build* machine — anything missing there is
silently left out, and the resulting binary still builds fine but exits
instantly the moment anyone runs it, with no visible error. `.venv` needs the
full transitive dependency list installed before building for the shipped
binary to be self-contained (see the apt-get list in
`.github/workflows/release.yml`, which is CI-verified by launching the built
binary inside a bare container). The only two libraries that can't be
bundled this way are `libEGL`/`libGL` — Qt loads them via `dlopen` rather
than linking them, so PyInstaller can never detect or bundle them. They're
left to resolve from the host's graphics driver, which every real Linux
desktop already provides — end users don't need to install anything.

The Linux build job is pinned to `runs-on: ubuntu-22.04` rather than
`ubuntu-latest` — PyInstaller bundles the build machine's own `libpython.so`,
which is linked against that machine's glibc, and glibc symbol versioning is
backwards-compatible only. Building on 24.04 (glibc 2.39) shipped a binary
that instantly failed with `GLIBC_2.38 not found` on anything older,
including Linux Mint 21.x (glibc 2.35) — a very much currently-supported,
widely-used release. 22.04 (glibc 2.35) costs nothing on newer systems while
covering a much wider range of real-world machines. The launch-check step
verifies against an `ubuntu:22.04` container specifically (not `latest`) so
a future runner bump can't quietly reintroduce the same regression.

## Crash/launch logging

A GUI app run by double-clicking has no terminal attached, so any failure —
including the glibc mismatch above — was previously invisible to the user
reporting it, leaving nothing to diagnose except reproducing their exact
environment by hand. `build_app.sh` now wraps the real executable in a
launcher script (`dist/xkoranate/xkoranate` on Linux,
`xkoranate.app/Contents/MacOS/xkoranate` on macOS; the real binary is
renamed to `xkoranate-bin` alongside it) that tees all output to
`launch.log` in a per-OS log directory — this is the only way to capture a
crash that happens before Python itself starts, since nothing in the app's
own code has run yet to catch it. [xkoranate/crashlog.py](xkoranate/crashlog.py)
additionally installs a `sys.excepthook` covering anything after Python
starts, writing a structured `app.log` (with OS/Python/glibc info) and
showing a native dialog pointing the user at it. See
[docs/getting-started.md](docs/getting-started.md#if-something-goes-wrong)
for the exact log paths. Windows only gets the Python-level `app.log` for
now — no wrapper script — since no equivalent pre-Python failure has been
observed there.

Tagged releases (`v*`) trigger `.github/workflows/release.yml`, which builds
all three platforms in CI and attaches the zipped artifacts to a draft GitHub
release. See [ROADMAP.md](ROADMAP.md) for the Windows-support feasibility
notes this was based on.

## Project layout

- `xkoranate/` — the application package; module layout mirrors the original
  C++ `src/` tree (paradigms, competitions, xml, eventeditor, signuplisteditor,
  rpeditor, tablegenerator).
- `sports/` — sport definition XML files (copied from the original repo).
- `PORTING.md` — the C++→Python porting conventions used throughout.
- `tests/integration_test.py` — end-to-end boot + scorinate + save/load check.

## Compatibility

- Scorination files (events/RP lists/signups) and table generator files written
  by the original program load unchanged, and files written by this port match
  the original format.
- Settings are stored under the same `thirdgeek.com/xkoranate` identifier, so
  directory preferences from an existing installation carry over.

## License

GNU General Public License v3.0 or later — see [LICENSE](LICENSE). This
project is a derivative of the original xkoranate-CE by Commerce Heights
(ThirdGeek); see [NOTICE.md](NOTICE.md) for full attribution and third-party
components.
