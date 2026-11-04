# Questions and answers

**Is xkoranate free?**

Yes. It's free and open source, made by volunteers for the NS Sports
community.

**Do files from the original xkoranate still work?**

Yes. Event files, sign-up lists, table generator files and exported
results all work in both programs, in either direction.

**Will I get the same results as the original program?**

Yes. xkoranate uses exactly the same maths and produces results in exactly
the same layout. If you find a difference, please
[report it](https://github.com/NS-Sports/xkoranate-ce-python/issues/new?template=bug_report.yml).

**Can I save my work in the middle of an event?**

Yes. Save at any point. Your sign-ups, groups and every result you've
generated so far are all kept in the file.

**Can I undo a result I didn't like?**

Click the dice on that round again to make new results. This replaces the
old ones, and xkoranate asks first. There is no way to get back the old
results once they've been replaced, unless you saved the file before you
did it.

**Should I re-roll results I don't like?**

That's up to your competition's rules. Most competitions expect the first
result to stand.

**How do I run a tournament with groups and then a knockout stage?**

Make one file for the tournament, with two events in it:

1. **Group Stage**: **Round robin**, with Group A, Group B and so on set
   up in step 4.
2. **Knockout**: **Single elimination**. Once the group stage is over,
   add the teams that went through to this event's sign-ups.

**How do I run a league split into conferences?**

Choose **Inter-conference round robin** in step 3, then make one group per
conference in step 4, named after it. Set how often teams meet inside their
conference and how often they meet the other conferences. See
[Conferences](building-an-event.md#conferences).

**How do I run heats and a final?**

Make one event per round. For the heats, put each heat in its own group in
step 4, and tick **Show overall ranking across all groups** in step 3 to
see who's fastest overall. Then make a final event with the qualifiers.

**My sport isn't listed. Can I add it?**

Not from inside the app yet. Sports are defined in files in the `sports`
folder that comes with xkoranate. Ask on the NS Sports forum or
[open a feature request](https://github.com/NS-Sports/xkoranate-ce-python/issues/new?template=feature_request.yml).
An in-app sport editor is
[planned](https://github.com/NS-Sports/xkoranate-ce-python/issues/27).

**Where do I report a bug or ask for a feature?**

Use the
[issue tracker on GitHub](https://github.com/NS-Sports/xkoranate-ce-python/issues/new/choose).
It has separate forms for bug reports and feature requests. The
[roadmap](https://github.com/NS-Sports/xkoranate-ce-python/blob/main/ROADMAP.md)
shows what's already planned.
