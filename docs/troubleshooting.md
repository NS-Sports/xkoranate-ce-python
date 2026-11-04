# Troubleshooting

Find your problem in the headings below. If nothing here helps,
[report a bug](#reporting-a-bug) and attach your log files.

## The app won't open

**"Windows protected your PC", "can't be opened" or "unidentified
developer".** Your computer is being careful with an app it doesn't
recognise. See [Open it the first time](getting-started.md#3-open-it-the-first-time).

**Nothing happens at all.** xkoranate writes a log file even when it fails
to start. Check the log (see [Log files](#log-files) below):

- If it mentions **glibc** (Linux only), your Linux is too old. You need
  Ubuntu 22.04, Linux Mint 21, Debian 12, Fedora 36 or newer.
- Otherwise, [report a bug](#reporting-a-bug) and attach the log.

**Windows: it says a file is missing.** Make sure you're running
`xkoranate.exe` from inside its own folder, with everything you unzipped
still next to it. Don't copy the `.exe` out on its own.

## Setting up events

**Continue is greyed out on step 1.** You've clicked a sport heading
rather than an event or formula you can play. Click the arrow next to it
and pick something inside.

**The format I want isn't in the step 3 list.** Each sport only offers
the formats that make sense for it. A 100 m race can't be a round robin,
for example. Check that you picked the right sport in step 1.

**A participant disappeared after I imported a file.** Lines with fewer
than three parts (name;team;skill) are skipped. Check that line in your
file. See [Importing sign-ups](building-an-event.md#importing-sign-ups-from-a-file).

**I have a participant called "Name".** Your file had a heading line.
Delete that row and remove the line from your file.

**"There is nothing to scorinate yet."** The event has no fixtures. Go
back to step 4 and check that your groups have participants in them, at
least two per group.

**I deleted an event by mistake.** Close the file and choose **Discard**
when asked about saving. The event is back when you reopen the file. This
only works if you haven't saved since deleting it.

## Results

**The view is blank after I changed the bracket.** Changing a knockout
draw deletes the results that were played from the old draw. Go to step 5
and play the rounds again.

**The columns are all over the place on the forum.** Tick **BBCode
output** before copying, so the results are wrapped in `[pre]` tags.

**The table generator shows a team twice.** The two spellings don't
match, for example "Aurelia" and "Aurelia (AUR)". Make every matchday's
names the same. See
[How results need to look](table-generator.md#how-results-need-to-look).

**Can I get the same results again?** No. Each scorination is random, like
playing the match for real. Once you've posted a result, keep the saved
file. It stores every result you've generated.

## Log files

If xkoranate crashes or won't start, it records what went wrong in a log
folder:

| Computer | Log folder |
|---|---|
| Windows | `%LOCALAPPDATA%\xkoranate\logs\` (paste this into the File Explorer address bar) |
| Mac | `~/Library/Logs/xkoranate/logs/` (in Finder, choose **Go › Go to Folder…** and paste it in) |
| Linux | `~/.local/state/xkoranate/logs/` |

There are up to two files in that folder:

- **`launch.log`** (Mac and Linux only) is the one to check when nothing
  happens at all.
- **`app.log`** records problems after the app has started.

## Reporting a bug

1. Go to the
   [bug report form](https://github.com/NS-Sports/xkoranate-ce-python/issues/new?template=bug_report.yml).
   You need a free GitHub account.
2. Say what you did, what you expected, and what happened instead.
3. Attach both log files (whichever exist) and, if you can, the `.xml`
   file you were working on.
