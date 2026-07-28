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

Some sports have more than one kind of participant, and show a tab per kind.
The Racing Scorinator has four — **Drivers**, **Teams**, **Tyres** and
**Engines** — because a car's ratings come from all of them combined. Fill in
the teams and manufacturers first, then point each driver at them: the Team
column matches a team by name, and the Tyres and Engines columns match a
manufacturer by its monogram (the single-letter code) or its full name. Hover a
column heading for what it means.

Leave a driver's Tyres or Engines blank — or type `Stock` — for a neutral
supplier that adds nothing to the car, which is what you want if your series
doesn't model suppliers at all. A team or manufacturer that a driver names but
that isn't on the list is flagged at the top of the results, since it would
otherwise quietly leave the car without those ratings.

## 3. Competition

Choose the competition format from the dropdown. Available formats depend on
the sport's paradigm, and include:

- **Mass start** — everyone races at once; results are times or placements.
- **Round robin** — every participant/team plays every other one.
- **Individual matches** — a fixed set of head-to-head matchups.
- **Multiple-run competition** — best-of-N attempts (e.g. gymnastics, diving).
- **Shooting competition** / **Archery ranking round** — precision-sport
  scoring formats.
- **Racing season** — a full calendar of race weekends, each with qualifying
  and a race, with drivers' and constructors' championships kept as you go.
- **Single race** — one race weekend at one circuit, optionally with a
  practice session in front of qualifying. Points still appear beside each
  finisher, so a one-off can be folded into a series scored elsewhere.

Some formats show an options widget here too (number of matchdays,
tiebreaker rules, and similar).

## 4. Groups

Organize participants into groups, brackets, or seeding pools, if the
competition format needs them. The toolbar lets you create a group, add one
or all participants to it, delete a group, and randomize group assignment.
Drag and drop to reorder within the tree.

Click **View full schedule** to preview the fixture list for competition
formats that have a fixed schedule (round robin, individual matches). Formats
without a fixed schedule (like mass start) will tell you there's nothing to
preview.

Some formats have no use for groups, because everyone who signed up is in the
event. Those replace this step with something they *do* need planning out, and
the breadcrumb is renamed to match:

- **Calendar** (Racing season) — one row per race week. A new season starts
  empty: name a circuit to add the week, clear the name to drop it. Naming one
  fills the rest of the row with neutral settings for you to adjust — lap
  record, length, aggressiveness, technicality, qualifying format and weather.
  **Type** and **Qualifying** are dropdowns. A week whose Type is `Testing`
  runs a practice session only and scores nothing. The week is titled "Grand
  Prix of" its host nation.
- **Circuit** (Single race) — the same settings for the one circuit, plus an
  optional event name and a switch for running a practice session first.

!!! tip "Something to start from"
    `examples/example-season.xml` in the repository is a complete twelve-round
    season — 30 drivers, 15 teams, tyre and engine manufacturers, every
    qualifying format and an RP list — ready to open and scorinate.

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
