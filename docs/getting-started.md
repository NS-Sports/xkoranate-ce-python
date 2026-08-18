# Getting started

## Download

Grab the build for your platform from the
[Releases page](https://github.com/NS-Sports/xkoranate-ce-python/releases).
Each release ships a build for macOS, Windows, and Linux.

| Platform | Archive | Run |
|---|---|---|
| macOS (Apple Silicon) | `xkoranate-<version>-macos-arm64.zip` | Unzip, then open `xkoranate.app` |
| macOS (Intel) | `xkoranate-<version>-macos-x86_64.zip` | Unzip, then open `xkoranate.app` |
| Windows | `xkoranate-<version>-windows.zip` | Unzip, then run `xkoranate\xkoranate.exe` |
| Linux | `xkoranate-<version>-linux.tar.gz` | Extract, then run `xkoranate/xkoranate` |

!!! note "Which Mac build do I need?"
    Apple Silicon Macs (M1/M2/M3/M4) need the `arm64` build; older Intel
    Macs need the `x86_64` build. Check via the Apple menu → About This Mac:
    it lists "Chip" (Apple Silicon) or "Processor" (Intel).

!!! note "Unsigned builds"
    These builds aren't code-signed or notarized, so your OS will likely warn
    you the first time you open one (macOS Gatekeeper, Windows SmartScreen).
    You'll need to explicitly allow the app to run — right-click → Open on
    macOS, or "More info" → "Run anyway" on Windows.

!!! note "Linux: nothing to install (on Linux Mint 21+ / Ubuntu 22.04+ or newer)"
    The Linux build ships with everything it needs already inside the
    `xkoranate/` folder — no system packages required on any regular Linux
    desktop. The one thing it can't bundle is your graphics driver
    (`libEGL`/`libGL`), but every desktop Linux install already has this,
    since it's needed to draw anything on screen at all.

    The build requires **glibc 2.35 or newer** (Linux Mint 21+, Ubuntu
    22.04+, Debian 12+, Fedora 36+, or comparably recent). This isn't
    something the app can bundle its way around — glibc is the C library
    everything else on the system links against, so it has to match what's
    already installed.

    If double-clicking `xkoranate/xkoranate` does nothing, check the log file
    — see [If something goes wrong](#if-something-goes-wrong) below.

## If something goes wrong

If xkoranate crashes, or double-clicking it does nothing at all, it still
writes a log file — no terminal required:

| Platform | Log location |
|---|---|
| Linux | `~/.local/state/xkoranate/logs/` |
| macOS | `~/Library/Logs/xkoranate/logs/` |
| Windows | `%LOCALAPPDATA%\xkoranate\logs\` |

There are two files worth checking:

- **`launch.log`** (macOS/Linux only) — everything the app printed, captured
  even if it failed before the app itself could start (e.g. an incompatible
  system library). This is the one to check first for "nothing happens."
- **`app.log`** — a structured record of anything that went wrong after the
  app started, including a full error trace and basic system info (OS,
  Python/Qt version).

If you're reporting an issue, please attach both files (whichever exist) —
it turns "it doesn't work" into something we can actually act on.

## The main window

When you launch xkoranate you land on the main window: a sidebar on the left
listing your **Events** and your **Bonuses** configuration, and a large
central area that shows whichever one is selected. A toolbar across the top
gives you the core actions:

| Button | Does |
|---|---|
| New file | Start a fresh document |
| Open file | Load a saved `.xml` document |
| Save / Save as | Save the current document |
| Table generator | Open the standalone [table generator](table-generator.md) window |
| Dark mode | Toggle light/dark theme (also in the **View** menu) |

A single xkoranate document (the `.xml` file you save) can contain **multiple
events** plus **one bonuses configuration** shared across all of them — you
don't need a separate file per event.

## What's next

- [Building an event](building-an-event.md) walks through the 5-step wizard
  used to set up and run a scorination.
- [Table generator](table-generator.md) covers the standalone tool for
  turning match results into league standings.
- [RP bonuses](rp-bonuses.md) explains the per-nation bonus configuration.
