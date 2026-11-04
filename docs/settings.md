# Files and settings

xkoranate has no settings window. It remembers two kinds of things for you.

## Your colour theme

Choose **View › Light**, **Dark** or **True Dark (OLED)**. True Dark uses
a pure black background, which suits phone-style OLED screens. Your choice
is kept the next time you open xkoranate.

## The last folder you used

Each kind of file opens in the folder you last used for it. The first
time, that's your home folder. xkoranate remembers these folders
separately:

| Kind of file | When it's remembered |
|---|---|
| Event files (`.xml`) | When you open or save an event file |
| Sign-up lists (`.txt`) | When you import sign-ups on step 2 |
| Exported results (`.txt`) | When you click **Export to file** on step 5 |
| Results for the table generator (`.txt`) | When you import match results into the table generator |
| Table files (`.xml`) | When you open or save in the table generator |

If you used the original xkoranate on the same computer, these folders
carry over automatically.

## Kinds of file

| Extension | What it is | Made by |
|---|---|---|
| `.xml` | An event file: all your events, sign-ups and results | **File › Save** |
| `.xml` | A table generator file: match results and table settings | **Save file** in the table generator |
| `.txt` | A sign-up list you can import | You, in any text editor ([format](building-an-event.md#importing-sign-ups-from-a-file)) |
| `.txt` | Exported results | **Export to file** on step 5 |

All of these work in the original xkoranate too.

## For the curious: where settings are stored

| Computer | Location |
|---|---|
| Windows | Registry, under `HKEY_CURRENT_USER\Software\thirdgeek.com\xkoranate` |
| Mac | `~/Library/Preferences/com.thirdgeek.xkoranate.plist` |
| Linux | `~/.config/thirdgeek.com/xkoranate.conf` |

The sport definitions live in the `sports` folder that comes with
xkoranate. There's one file per sport. You can edit them by hand, but
it's easy to break a sport that way, so keep a backup.
