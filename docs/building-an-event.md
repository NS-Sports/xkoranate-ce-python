# Building an event

Click **New event** in the sidebar to start the 5-step wizard: **Sport →
Signups → Competition → Groups → Scorinate**. A breadcrumb across the top of
the window tracks which step you're on, and **Back**/**Next** move between
them.

## 1. Sport

Pick a sport from the tree on the left. Sports are organized by discipline
(athletics, football codes, racket sports, and so on) — expand a category to
see the individual events inside it.

Under the hood, each sport is wired to a scoring engine (a "paradigm") that
determines how results come out: some produce head-to-head match scores,
others produce race times or placements. You don't need to know which engine
a sport uses — picking the sport is enough, and the rest of the wizard adapts
to it automatically.

Some sports show extra options below the sport tree once selected — for
example, several football-code sports let you turn on **home advantage** and
set its magnitude. These options are sport-specific and only appear when
relevant.

## 2. Signups

Add the athletes or teams competing. You can:

- Add participants one at a time with **Add participant**.
- Import a roster in one go with **Import from text file** — a semicolon-delimited
  `.txt` file, one participant per line: `name;nation;skill` (extra columns
  are supported for sport-specific attributes like style mods).

Use the min/max skill filters to narrow which imported participants are
eligible, if your source file has a wider range than you want to use.

## 3. Competition

Choose the competition format from the dropdown. Available formats depend on
the sport's paradigm, and include:

- **Mass start** — everyone races at once; results are times or placements.
- **Round robin** — every participant/team plays every other one.
- **Individual matches** — a fixed set of head-to-head matchups.
- **Single elimination** — a knockout bracket: losers go out, and each round's
  fixtures come from the winners of the round before it. Offered for any sport
  whose paradigm can run individual matches. Its options widget can add a
  third-place playoff, played as its own matchday before the final.
- **Multiple-run competition** — best-of-N attempts (e.g. gymnastics, diving).
- **Shooting competition** / **Archery ranking round** — precision-sport
  scoring formats.

Some formats show an options widget here too (number of matchdays,
tiebreaker rules, and similar).

## 4. Groups

Organize participants into groups, brackets, or seeding pools, if the
competition format needs them. The toolbar lets you create a group, add one
or all participants to it, delete a group, and randomize group assignment.
Drag and drop to reorder within the tree.

### Setting a bracket

For **Single elimination** this step is titled **Bracket** and arranges the
first-round draw instead. Matches aren't created by hand — the bracket size
makes them — so the create-group and add-one-participant buttons are hidden,
and **Delete** empties the selected slot rather than removing it.

- The **x-participant bracket** dropdown sets how many slots the bracket has.
  Any slot you don't fill is a **bye**: the participant opposite it advances
  unopposed. Byes are entrants in their own right — you can drag them around,
  or pick one from a slot's dropdown, to keep a particular slot open.
- Three toolbar buttons arrange the draw once, after which you can adjust it
  by hand: the **dice** draws at random, **Seed the draw by skill** puts the
  strongest against the weakest so the top two can only meet in the final, and
  **Keep the top seeds apart** asks how many seeds to spread across the
  bracket and draws everyone else around them.

Changing the bracket after you have scorinated discards the results played
from it, since they describe a draw that no longer exists. You'll be asked
before that happens.

Click **View full schedule** to preview the fixture list for competition
formats that have a fixed schedule (round robin, individual matches, single
elimination). For a bracket the whole thing is shown, with later rounds
reading "Match 9 winner v Match 10 winner" until they're known. Formats
without a fixed schedule (like mass start) will tell you there's nothing to
preview.

## 5. Scorinate

This is where you actually run the simulation:

- **Scorinate event** generates results for the current matchday/round.
  You'll be warned before overwriting results you've already generated.
- **View match odds** shows fixture-by-fixture win probabilities based on
  participant skill (available for competition formats that support it).
- Use the matchday dropdown to switch between rounds once you have more
  than one.
- **Export to file** saves the results as a `.txt` file, ready to post.

Check **BBCode output ([pre] tags, bold winners)** before exporting or
copying if you're posting straight to the forum — it wraps the results in
`[pre]` tags and automatically bolds each match's winner.
