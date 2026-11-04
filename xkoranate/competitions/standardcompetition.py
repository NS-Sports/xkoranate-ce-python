from xkoranate.competitions.abstractcompetition import XkorAbstractCompetition
from xkoranate.variant import toList, toString


class XkorMassStartCompetition(XkorAbstractCompetition):
    def hasOptionsWidget(self):
        return True

    def matchdays(self):
        return 1

    def matchdayNames(self):
        return ["Mass start"]

    def newOptionsWidget(self, competitionOptions):
        from xkoranate.competitions.options.massstartcompetitionoptions import XkorMassStartCompetitionOptions

        return XkorMassStartCompetitionOptions(competitionOptions)

    def sortsResults(self):
        return toString(self.userOpt.get("sortResults", "true")) == "true"

    def scorinate(self, matchday):
        from xkoranate.paradigms.paradigmfactory import XkorParadigmFactory

        localParadigmOptions = dict(self.paradigmOpt)
        localParadigmOptions["nameWidth"] = self.nameWidth()

        p = XkorParadigmFactory.newParadigmForSport(self.sport, localParadigmOptions)

        allResults = []
        heatResults = []
        self.resultsBuf[matchday] = ""
        for i in range(len(self.startList.groups)):
            p.scorinate(list(self.startList.groups[i].athletes))
            # C++ copies the results vector before mutating it
            groupResults = [r.clone() for r in p.results()]
            for j in groupResults:
                j.result["heat"] = i  # set the heat number so that the sorting works out correctly
            if self.sortsResults():
                p.comparisonFunction().sort(groupResults)
                self.resultsBuf[matchday] += self.rankedListOutput(self.startList.groups[i].name, groupResults, p.comparisonFunction())
            else:
                self.resultsBuf[matchday] += self.startList.groups[i].name + "\n"
                self.resultsBuf[matchday] += p.output() + "\n\n"
            allResults.extend(groupResults)
            heatResults.append(groupResults)

        if self.sortsResults():
            self.resumeOpt["heatRanks"] = self.heatRanks(heatResults, allResults, p.comparisonFunction())

        # do the complete ranking
        if self.sortsResults() and toString(self.userOpt.get("overallRanking", "false")) == "true":
            p.comparisonFunction().sort(allResults)
            self.resultsBuf[matchday] += self.rankedListOutput("Overall ranking", allResults, p.comparisonFunction())

    @staticmethod
    def heatRanks(heatResults, allResults, comparator):
        """Each result's rank across every heat, per heat in the order its
        lines were written ("" for one that can't be ranked). Saved with the
        event so formatQualifications() can compare the next-placed finishers
        of different heats without the results themselves."""
        ranked = list(allResults)
        comparator.sort(ranked)
        overall = {}
        prev = None
        rank = 0
        for i, r in enumerate(ranked):
            if not comparator.isRankable(r):
                overall[id(r)] = ""
                continue
            if prev is None or comparator(prev, r) or comparator(r, prev):
                rank = i + 1  # otherwise tied with the result above
            overall[id(r)] = str(rank)
            prev = r
        return [[overall[id(r)] for r in heat] for heat in heatResults]

    def supportsQualifications(self):
        # unsorted output has no ranks to qualify by
        return self.sortsResults()

    def formatQualifications(self, text, matchday, settings):
        from xkoranate.competitions.qualification import leagueMarkers

        if not text or not settings.isEnabled() or not self.supportsQualifications():
            return text

        lines = text.split("\n")
        heats = []  # (header line, result lines, QualificationGroup)
        pos = 0
        for heatNo, g in enumerate(self.startList.groups):
            parsed = self._parseHeat(lines, pos, heatNo, g.name, len(g.athletes))
            if parsed is None:
                # can't tell which lines are this heat's; marking the others
                # alone could misjudge who comes next-placed, so mark nothing
                return text
            heats.append(parsed)
            pos = parsed[1][-1] + 1 if parsed[1] else parsed[0] + 1

        heatRanks = toList(self.userOpt.get("heatRanks"))

        def crossRank(candidates):
            ranks = []
            for heatNo, team in candidates:
                saved = toList(heatRanks[heatNo]) if heatNo < len(heatRanks) else []
                if len(saved) != len(heats[heatNo][1]) or not toString(saved[team[1]]).isdigit():
                    return None  # saved before ranks were kept, or out of step
                ranks.append((int(toString(saved[team[1]])), (heatNo, team)))
            ranks.sort(key=lambda x: x[0])
            bins = []
            for i, (rank, candidate) in enumerate(ranks):
                if i > 0 and rank == ranks[i - 1][0]:
                    bins[-1].append(candidate)
                else:
                    bins.append([candidate])
            return bins

        markers = leagueMarkers([h[2] for h in heats], settings, crossRank)

        for (header, resultLines, _group), heatMarkers in zip(heats, markers):
            if not heatMarkers:
                continue
            width = max(len(lines[i]) for i in [header] + resultLines)
            for j, i in enumerate(resultLines):
                marker = heatMarkers.get((header, j))
                if marker:
                    lines[i] = lines[i].ljust(width) + " " + marker
        return "\n".join(lines)

    @staticmethod
    def _parseHeat(lines, pos, heatNo, name, count):
        """Find a heat's block as rankedListOutput() wrote it — a header of
        spaces then the heat name, then one line per entrant led by its rank —
        at or after line `pos`. Returns (header, result lines, group) or None."""
        from xkoranate.competitions.qualification import (QualificationGroup,
                                                          parseRankToken)

        for header in range(pos, len(lines) - count):
            line = lines[header]
            title = line.lstrip(" ")
            spaces = len(line) - len(title)
            if title != name or spaces < 2:
                continue
            digits = spaces - 1
            resultLines = list(range(header + 1, header + 1 + count))
            tokens = []
            for i in resultLines:
                row = lines[i]
                token = parseRankToken(row[:digits]) if len(row) > digits and row[digits] == " " else None
                if token is None:
                    break
                tokens.append(token)
            else:
                # teams are keyed by (header line, position in the heat) —
                # unique, and names can repeat across heats
                teams = [(header, j) for j in range(count)]
                order, excluded = [], []
                unrankable = False
                for team, token in zip(teams, tokens):
                    if token == "—" or (token == "" and unrankable):
                        unrankable = True
                        excluded.append(team)
                    elif token == "":
                        if not order:
                            break  # a tie with nothing above it: not ours
                        order[-1].append(team)
                    else:
                        order.append([team])
                else:
                    return header, resultLines, QualificationGroup(
                        teams=teams, order=order, excluded=excluded)
        return None
