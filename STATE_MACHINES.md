# xkoranate-CE — State machines

A map of every place the app keeps state that changes in steps: the explicit
machines (a wizard with numbered steps) and the implicit ones (a pair of
flags, a cached copy that has to agree with another copy). For each one:
its states, the invariants that should always hold, and the transitions that
move it. The last sections list the invalid states the code could actually
reach, with the evidence, and the gaps that are known but left alone.

How to read the transition tables: **From** and **To** are states, **Event**
is what triggers the move (a click, a signal, a method call), **Guard** is the
condition checked first, and **Effect** is what changes besides the state.

## Where concurrency and retries come from

The app is single-threaded. Nothing runs in parallel, but work can still
interleave in four ways, and each one shows up in the tables below:

| Source | Where | What can interleave |
|---|---|---|
| Deferred calls | `QTimer.singleShot(0, …)` in `eventsetupwidget.scheduleReflow` and `treewidget.dropDownEditor` | The call runs on a later trip round the event loop, after other signals have changed the state it was queued for. |
| Nested event loops | `QMessageBox.exec()` in `ui/dialogs.confirm` and `ask_save_changes`, `QFileDialog.exec()` in `ask_file_name`, `QInputDialog.getInt` | While a modal dialog is up, queued timers and posted events still run. A handler that asks a question can be re-entered before it gets its answer. |
| Non-blocking dialogs | `ui/dialogs.open_file_dialog`, the results export dialog in `scorinatewidget.exportResults` | The chosen file arrives later through `fileSelected`, after the call that opened the dialog has returned. |
| A second window | the table generator (`XkorApplication.tg`) | It stays usable while the main window shows a window-modal dialog, and has its own document state. |

Retries are user-driven: regenerating a matchday (revert, then replay),
answering Cancel and trying again, saving again after a failed save,
reopening the table generator.

---

## 1. Main document (`centralwidget.py`, `application.py`, `mainwindow.py`)

State: `currentFileName` (empty means untitled) × `modified`.

| State | `currentFileName` | `modified` | Window title |
|---|---|---|---|
| Untitled, clean | `""` | False | `untitled` |
| Untitled, modified | `""` | True | `untitled*` |
| Saved, clean | path | False | file name |
| Saved, modified | path | True | file name `*` |

Invariants

- `XkorCentralWidget.modified` equals `XkorApplication.modified` equals the window's `[*]` marker. `setModified(True)` emits `fileEdited`; `False` only ever arrives through `fileChanged`, which `setFileName` turns into `setModified(False)`.
- `okayToLoad()` returns True only if the document is clean, or the user discarded it, or a save succeeded.
- A save that fails leaves the file on disk as it was before the save.

| From | Event | Guard | To | Effect |
|---|---|---|---|---|
| any | edit in any editor (`dataChanged`, `listChanged`) | not loading | same file, modified | `fileEdited` |
| any | New | `okayToLoad()` | Untitled, clean | editors reset, navigation rebuilt |
| any | Open (dialog) | `okayToLoad()` | unchanged until a file is chosen | non-blocking dialog; `openFile(path)` runs later |
| any | `openFile(path)` | file parses | Saved, clean | editors reset, navigation rebuilt |
| any | `openFile(path)` | parse error | unchanged | error box |
| Untitled, * | Save | — | Save As | — |
| any | Save / Save As | write succeeds | Saved, clean | `eventDirectoryChanged` |
| any | Save / Save As | write fails | unchanged | error box; file on disk untouched |
| any | Save As | dialog cancelled | unchanged | — |
| any | close window / Quit | `okayToLoad()` | closed | — |

## 2. Navigation and the editor pane (`navigationwidget.py`, `centralwidget.py`)

State: which tree item is selected (BONUSES, an event, nothing), which editor
the stacked widget shows, and `currentEvent`, the stored event the event
editor is working on.

Invariants

- The event editor holds a *copy* of `currentEvent`. `updateCurrentEvent()` writes the copy back before the editor is pointed at anything else, and before every save.
- An event's name lives in the tree item; `updateEventNames()` copies it into the event on every `events()` call.
- `isInUse` suppresses `editItem` while the tree is being changed in code.

| From | Event | Guard | To | Effect |
|---|---|---|---|---|
| any | select BONUSES | — | RP editor shown | `editRPList` |
| any | select event E | E is in `m_events` | event editor on E | old copy written back, then `ee.setData(E)` |
| any | New event | — | event editor on the new event | `initEvent` emits `editEvent`; tree item opened for renaming |
| event E | Remove | — | the neighbour Qt selects, or BONUSES | `correctSelectionAfterDelete`; E stays in `m_events` but leaves the saved list |

## 3. Event editor wizard (`eventeditor/eventeditor.py`)

Five steps on a `QStackedLayout`: 0 Sport, 1 Signups, 2 Competition,
3 Groups (named Bracket or Conferences for those formats), 4 Scorinate.

Invariants

- **Go Back** is enabled exactly when the step is above 0.
- **Continue** is enabled exactly when the step is below 4 and a sport is selected.
- The step indicator names the step on screen.
- Showing an event only changes it to match what the editor will actually run. For example, a competition type the sport's paradigm can't run is replaced by the one the selector shows. An event whose sport file isn't installed can't be run at all, so `data()` hands it back exactly as loaded until the user picks a sport.
- `isLoading` is True for the whole of `setData`, so nothing it does marks the file modified.

| From | Event | Guard | To | Effect |
|---|---|---|---|---|
| any | `setData(event)` | — | 0 | selectors rebuilt from the event; buttons recomputed |
| 0 | select a sport | — | 0 | Continue enabled; signup and competition pages rebuilt |
| 0 | clear the sport | — | 0 | Continue disabled |
| n < 3 | Continue | sport selected | n + 1 | — |
| 3 | Continue | sport selected | 4 | `updateData()`, then `scorinateWidget.setEvent()` |
| n > 0 | Go Back | — | n − 1 | — |
| 2 | change competition type | — | 2 | setup page relabelled; groups pooled into a bracket or split back out |

## 4. Loading guards (implicit two-state machines)

Several widgets carry a flag that means "the change in progress came from
code, not the user". Each is a two-state machine, Interactive ⇄ Loading,
and the invariant is the same everywhere: while Loading, the widget emits no
`dataChanged`/`listChanged`, so a load never marks the file modified.

| Flag | Owner | Set by | Notes |
|---|---|---|---|
| `isLoading` | `XkorEventEditor` | `setData` | Also gates the editor's own `setDataChanged`. |
| `isLoading` | `XkorSignupListEditor` | `setData`, `setSport` | `setSport` saves and restores it. Its call to `setData` sets it False before `setSport` finishes, which is harmless today because nothing between that point and the restore emits while a load is in progress. |
| `isLoading` | `XkorRPEditor` | `setData` | Also governs whether changing the bonus formula asks first (§9). |
| `isLoading` | `XkorSportSelector` | `updateSportList` | `try`/`finally`. |
| `isInUse` | `XkorAbstractTreeWidget` subclasses | each tree edit | Set and cleared by hand, not saved and restored. Code that sets it must not call anything that also sets and clears it. |

## 5. Bracket setup (`eventeditor/eventsetupwidget.py`, bracket mode)

Three machines share this page when the competition is single elimination.

**Layout.** The tree holds matches of exactly two slots. A slot holds a
participant id or `BYE_ID`. `bracketSlotCount` is the size the user chose
(0 means size to fit). `_lastLaidSlots` is the last layout the code itself put
there, which is what a refused change goes back to.

Invariants

- The slot count is a power of two, and every match has two slots.
- No participant appears twice.
- Taking a participant out of the bracket leaves a bye in their slot. It never shifts anyone else into another match.

**Results guard.** Guards changes that would throw away results already
played from the bracket (`resultsGuard`, set by the event editor).

| State | Meaning |
|---|---|
| Not asked | The next structural change asks first. |
| Asking | A question is on screen. Its dialog runs a nested event loop. |
| Accepted | The user chose Discard. Further changes go ahead without asking until another event is loaded. |

| From | Event | To | Effect |
|---|---|---|---|
| Not asked | structural change | Asking | dialog |
| Asking | Discard | Accepted | change applied |
| Asking | Cancel | Not asked | change refused; a drag is undone |
| Asking | another change arrives (re-entry) | Asking | refused; the question already on screen decides |
| Accepted | structural change | Accepted | applied |
| any | `setGroups` (another event loaded) | Not asked | — |

**Reflow.** A drag moves rows with `takeChild` + `insertChild`, so one drop
fires `rowsRemoved` and then `rowsInserted`. Each one used to queue its own
deferred `reflowBracket`.

| From | Event | Guard | To |
|---|---|---|---|
| Idle | rows inserted/removed | not `isInUse`, bracket mode | Pending (one timer) |
| Pending | more rows inserted/removed | — | Pending (no second timer) |
| Pending | timer fires | — | Running → Idle |

Invariant: at most one reflow is queued at a time.

**Format memory.** `_groupsBeforeBracket` holds the pools from before the
format was switched to a bracket. They are put back when it is switched away,
if the bracket still holds the same participants. `reset()` clears it when
another event is loaded.

## 6. Scorination progress (`eventeditor/scorinatewidget.py` + `competitions/`)

State: `lastMatchday` (L, the last matchday with results, −1 for none), the
matchday picked in the dropdown (S), the event's `results` (matchday → text),
and the resume options in the event's competition options (the played-match
data each competition rebuilds itself from). The widget keeps its own copy
of the event (`self.e`) and the competition built from it (`self.c`). It sends
changes to the editor's copy through `resultConfirmed` and
`resumeFileOptionsSet`.

Invariants

- Results exist for exactly matchdays 0…L. `XkorEvent.setResult(md)` blanks everything after md.
- The resume options describe exactly the matches played on matchdays 0…L.
- `matchdays() ≥ 0`. A competition with nobody in it has nothing to scorinate.
- Results only count for the competition type that produced them. Each scorination stamps its type into the resume options (`resultsCompetition`). A competition built with another type's stamp discards the stored results and resume data, the same way a rearranged bracket does (§7).
- `self.c` is rebuilt from `self.e` after every matchday, as the GUI always has.

| From | Event | Guard | To | Effect |
|---|---|---|---|---|
| any | `setEvent` | — | L = last matchday with results | competition rebuilt, dropdown refilled |
| any | Scorinate | nobody to scorinate, or `matchdays() ≤ 0` | unchanged | "nothing to scorinate" box |
| L | Scorinate, S = L + 1 | — | S | one matchday played |
| L | Scorinate, S > L + 1 | user confirms filling the gap | S | L + 1…S played in order |
| L | Scorinate, S = L | user confirms | S | S reverted, then replayed |
| L | Scorinate, S < L | user confirms losing S…L | S | `revertToMatchday(S)`, then S replayed |
| any | qualification controls change | — | unchanged | options saved; display only |

Regenerating is the retry path. `revertToMatchday(S)` returns resume options
trimmed to matchdays before S. The widget applies them to its own copy at once,
and to the editor's copy when the replayed matchday is confirmed.

## 7. Single-elimination bracket (`competitions/singleeliminationcompetition.py`, `bracketresults.py`)

State: `_draw` (the first-round slot list, or None), `_rows` (played matches),
and the stored `bracketDraw`, `bracketResults` and `bracketThirdPlace`
options.

| Draw state | Meaning | Results |
|---|---|---|
| None | nothing played yet | none |
| Current | the stored draw matches the one the editor's slot order produces, and the third-place setting is unchanged | kept |
| Stale | the bracket was rearranged, or the playoff was turned on or off, after the draw was stored | dropped (`_loadState`) |

`MatchdaySchedule` fixes the running order: each round in turn, with the
third-place playoff played just before the final when it is enabled. A
round's fixtures exist only once the round before it is complete.
`revertToMatchday(md)` keeps the rows from matchdays before md, and drops the
draw when md is 0.

## 8. Format qualifications (`competitions/qualification.py`, `scorinatewidget.py`)

`off` → `top` (places per group) → `topPlusBest` (plus the best few from the
next place down). The setting is display-only: it changes how standings are
marked, never the stored results. It is saved with the competition options.

## 9. RP bonus formula (`rpeditor/rpeditor.py`)

State: the formula dropdown (`olympic`, `relative`, `wc36`),
`m_currentRPCalcType` (the formula the bonus widget was built for), and the
bonus widget itself.

Invariants

- `m_currentRPCalcType` equals the dropdown's formula, and the widget type matches it: `wc36` uses the World Cup 36 widget, the others the Olympic one.
- Loading a bonus list shows that list's formula and bonuses. It asks no questions and changes nothing in the list.

| From | Event | Guard | To | Effect |
|---|---|---|---|---|
| F | user picks formula G ≠ F | no bonuses, or user confirms | G | bonus widget rebuilt empty |
| F | user picks formula G ≠ F | user cancels | F | dropdown put back |
| F | `setData(list)` | — | the list's formula | widget rebuilt for it, then filled from the list |

## 10. Signup ceiling (`signuplisteditor/signuplisteditor.py`)

`_maxRankMode()` is one of `fixed` (the paradigm calibrates itself, e.g.
LISA: min 0, max 1), `pinned` (max follows the highest participant), or
`manual` (the organiser sets it). It is derived from the paradigm's
`usesMinSkill`/`usesMaxSkill` and the pin box. The pin box is only reset when
those capabilities change, so a paradigm-options edit doesn't clobber the
user's choice.

## 11. Table generator (`tablegenerator/tablegenerator.py`, `application.py`)

The table generator's document works like §1 (`fileModified`,
`currentFileName`). `matchesModified` marks the match text as needing a
re-parse. The OT/SO points boxes are each *linked* (following the win/loss
box) or *overridden*.

The window itself:

| State | `app.tg` |
|---|---|
| None | `None` |
| Open | a visible window |
| Closed | a hidden window, whose close was already accepted |

| From | Event | Guard | To | Effect |
|---|---|---|---|---|
| None | Table generator | — | Open | new window |
| Open | Table generator | its close is accepted (clean, Discard, or saved) | Open (new window) | old window deleted |
| Open | Table generator | the user cancels | Open (same window) | raised; nothing lost |
| Closed | Table generator | — | Open (new window) | old window deleted; its close was already answered |
| Open | close the window | `okayToLoad()` | Closed | — |

---

## Invalid states the code could reach

Each one was reproduced before it was fixed, and the regression tests named
here fail without the fix. Issue numbers are on
[NS-Sports/xkoranate-ce-python](https://github.com/NS-Sports/xkoranate-ce-python/issues).

| # | Machine | Invalid state or transition | How it's reached | Impact | Issue | Regression test |
|---|---|---|---|---|---|---|
| 1 | §1 | A failed save leaves the previous file truncated or half-written. | Any write error after the file is opened, e.g. a full disk. `QFile.open(WriteOnly)` empties the file before anything is written. | Data loss | #75 | `test_saving.py::test_a_failed_save_leaves_the_previous_file_intact` |
| 2 | §11 | The table generator is deleted with unsaved changes the user chose to keep. | Edit a table, click Table generator again, answer Cancel. `tableGenerator()` ignored `close()`'s answer and called `deleteLater()` anyway. | Data loss | #75 | `test_tablegenerator.py::test_reopening_keeps_a_table_the_user_chose_not_to_discard` |
| 3 | §3 | Showing an event whose sport file isn't installed rewrites its sport, paradigm and competition type. | Open a file whose event names a sport that's missing or renamed, select the event, save. The selector finds no sport, so `updateSport` stored `""`, and the competition selector fell back to its default type. | Data loss | #76 | `test_eventeditor.py::test_showing_an_event_with_a_missing_sport_leaves_it_alone` |
| 4 | §9 | Loading a bonus list asks "reset all bonuses?". Cancel leaves the dropdown on the old formula, and the next `updateData()` writes that formula into the list just loaded. | Open a file whose bonus formula differs from the one on screen (or New after one), when the screen has bonuses. | Corrupt RP settings | #76 | `test_rpeditor.py::test_loading_a_bonus_list_asks_nothing_and_shows_its_formula` |
| 5 | §5 | Cancel on "discard results?" is overridden by a reflow re-entered from the dialog's own event loop. | A drag fires `rowsRemoved` and `rowsInserted`, queueing two reflows. The first asks; the second runs inside that dialog, sees the guard already marked asked, and applies the drag. The first then "restores" the layout the second just laid. | Results lost after Cancel | #77 | `test_bracketeditor.py::test_a_declined_drag_is_not_overridden_by_a_queued_reflow` |
| 6 | §5 | After one Cancel, the next change discards the results without asking. | `confirmBracketChange` marked the guard asked before asking, whatever the answer. | Results lost silently | #77 | `test_bracketeditor.py::test_declining_does_not_silence_the_next_question` |
| 7 | §5 | Deleting a signup who is in the bracket shifts every later entrant into a different match. | `deleteAthlete` removed the row; the reflow then padded a bye onto the end. | Wrong draw | #77 | `test_bracketeditor.py::test_deleting_a_signup_leaves_a_bye_in_their_slot` |
| 8 | §6 | Results from another competition type are shown under this type's round names, and play continues from them. | Scorinate a round robin, then switch to single elimination or mass start. Switching back to the round robin after scorinating the other type counted the old matches twice. | Wrong results | #78 | `test_competitiontype.py` |
| 9 | §6 | `matchdays() == −1`. Scorinate asks "regenerate ?" and stores a result under matchday −1. Archery, multiple-run and shooting raise `IndexError` with no groups. | Scorinate an event with no participants in its groups. | Nonsense prompt, crash | #78 | `test_scorinatewidget.py` |
| 10 | §3 | Continue enabled with no sport selected. The wizard reaches Scorinate with an empty sport. | Be past step 0 on one event, select an event with no sport, click Go Back. `setData` reset the step but not the Go Back button, and `goPrev` enabled Continue unconditionally. | Invalid wizard state | #78 | `test_eventeditor.py::test_loading_an_event_resets_go_back` |

## Known gaps, left alone on purpose

- **Changing groups or the sport after scorinating keeps the results.** Unlike a competition-type switch, this is often deliberate: fixing a typo in a team name, or moving to a newer version of the same sport file. Bracket changes are the exception (§5, §7), because a bracket that no longer matches its results can't be continued. Discarding results on every group edit is a product decision, not a bug fix.
- **Deleting a signup who is in a scorinated bracket drops the bracket's results without a warning on the Signups page.** The participant has already gone by the time the bracket hears about it, so the guard can't offer a real Cancel. The warning belongs where the deletion happens.
- **Scorinating isn't atomic.** If a paradigm raises partway through a matchday, `self.c` keeps half-written state. A retry on the same object appends to it, for example round-robin output appended to a partial `resultsBuf` entry. No reachable trigger is known now that empty events are refused (row 9); the robust fix is to rebuild `self.c` on any exception.
