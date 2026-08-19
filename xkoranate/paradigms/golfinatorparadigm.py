from ..result import XkorResult
from ..variant import qNumber, toDouble, toInt, toList, toString
from .abstractparadigm import XkorAbstractParadigm


class XkorGolfinatorParadigm(XkorAbstractParadigm):
    def __init__(self, sport=None, userOptions=None):
        super().__init__(sport, userOptions)
        self.supportedCompetitions["standard"] = True

    def hasOptionsWidget(self):
        return True

    def newAthleteWidget(self):
        from ..signuplisteditor.athletewidget import XkorAthleteWidget
        return XkorAthleteWidget(["name", "nation", "skill", "style"],
                                 ["Participant", "Team", "Skill", "Style"],
                                 ["string", "string", "skill", "golfStyle"])

    def newOptionsWidget(self, paradigmOptions):
        from .options.golfinatorparadigmoptions import XkorGolfinatorParadigmOptions
        return XkorGolfinatorParadigmOptions(paradigmOptions)

    def scorinate(self, athletes, previousResults=None):
        # load options
        nameWidth = toInt(self.userOpt.get("nameWidth", 20)) + 2
        resultWidth = toInt(self.opt.get("resultWidth", 1)) + 1

        holes = toInt(self.opt.get("holes", 18))
        yardage = toList(self.userOpt.get("yardage", [435, 529, 198, 517, 451, 408, 178, 457, 414, 495, 505, 155, 614, 435, 478, 381, 455, 357]))
        par = toList(self.userOpt.get("par", [4, 5, 3, 5, 4, 4, 3, 4, 4, 4, 4, 3, 5, 4, 4, 4, 4, 4]))
        differential = toList(self.userOpt.get("differential", [0.19, -0.36, 0.15, 0, 0.23, 0.19, 0.24, 0.13, 0.18, 0.23, 0.32, 0.3, -0.14, 0.25, 0.35, 0.19, 0.63, -0.46]))
        sand = toList(self.userOpt.get("sand", [1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0]))
        water = toList(self.userOpt.get("water", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]))
        narrow = toList(self.userOpt.get("narrow", [0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0]))
        green = toList(self.userOpt.get("green", [0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0]))

        # initialize results
        self.out = []
        self.res = []

        for athlete in athletes:
            r = XkorResult()
            r.athlete = athlete.clone()

            # get athlete’s style
            style = toString(r.athlete.property("style"))
            length = toInt(style[0:1])
            accuracy = toInt(style[1:2])
            longIrons = toInt(style[2:3])
            shortIrons = toInt(style[3:4])
            wedges = toInt(style[4:5])
            putting = toInt(style[5:6])

            attempts = []
            totalScore = 0
            for i in range(holes):
                # hole parameters
                holePar = toInt(par[i])
                holeYards = toDouble(yardage[i]) / 800.0
                holeDifferential = toDouble(differential[i])
                longIronMultiplier = 1 + toInt(water[i]) + toInt(narrow[i])
                shortIronMultiplier = 1 + toInt(narrow[i]) + toInt(green[i])
                wedgeMultiplier = 1 + toInt(sand[i]) + toInt(green[i])

                # calculate skill for this hole
                holeSkill = 6.5 + ((longIronMultiplier * longIrons
                                    + shortIronMultiplier * shortIrons
                                    + wedgeMultiplier * wedges)
                                   / (longIronMultiplier + shortIronMultiplier + wedgeMultiplier))

                # rpSkill * 2 because the original formula uses rank + RP
                magicNumber = (r.athlete.rpSkill * 2
                               + (6.5 + length * holeYards + accuracy * (1 - holeYards)
                                  + holeSkill * (holePar - 2.5)) / (holePar - 1.5))
                magicNumber = magicNumber * 0.06 + 0.02
                puttingNumber = 0.66 - 0.04 * putting

                rand1 = self.s.randUniform()
                rand2 = self.s.randUniform()
                rand3 = self.s.randUniform()

                adjustment = 0
                if rand1 < 0.02:
                    shotsToGreen = holePar - 3
                elif rand1 > 0.98:
                    shotsToGreen = holePar
                elif rand1 < magicNumber:
                    shotsToGreen = holePar - 2
                else:
                    shotsToGreen = holePar - 1

                if rand2 < puttingNumber:
                    putts = 2
                elif rand2 > 0.95:
                    putts = 3
                else:
                    putts = 1

                if rand3 < abs(holeDifferential):
                    adjustment = 1 if holeDifferential > 0 else -1

                score = shotsToGreen + putts + adjustment
                if score == 0:
                    score += 1  # you can’t finish the hole in zero strokes!

                attempts.append(score)
                totalScore += score
            r.result["attempts"] = attempts
            r.setScore(totalScore)
            r.setOutput(self.outputLine(r, nameWidth, resultWidth))
            self.res.append(r)
        self.generateOutput()

    # protected:

    def individualResult(self, a, b, c=None):
        return XkorResult()  # unused

    def outputLine(self, r, nameWidth=None, resultWidth=None):
        # C++ declares outputLine(XkorResult, double, double), which hides but
        # does not override the base outputLine(XkorResult); calls through the
        # base interface (e.g. addResults) use the base implementation
        if nameWidth is None:
            return super().outputLine(r)

        rval = self.formatName(r.athlete).ljust(int(nameWidth))
        attempts = toList(r.value("attempts"))

        for i in range(len(attempts)):
            rval += toString(attempts[i]).rjust(int(resultWidth))
        rval += qNumber(r.score()).rjust(int(resultWidth) + 3)
        return rval
