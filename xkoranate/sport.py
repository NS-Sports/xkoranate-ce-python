import math
import sys


class XkorSport:
    def __init__(self):
        self.m_name = ""
        self.m_alphaName = ""
        self.m_discipline = ""
        self.m_event = ""
        self.m_scorinator = ""
        self.m_paradigm = ""
        self.m_paradigmOptions = {}
        self.m_dataPoints = {}  # key -> {x: y} (iterated in sorted-key order)
        self.r = None  # Mt19937

    def addDataPoints(self, key, value):
        self.m_dataPoints[key] = value

    def alphabetizedName(self):
        if self.m_alphaName:
            return self.m_alphaName
        else:
            return self.m_name

    def countValues(self):
        return len(self.m_dataPoints)

    def discipline(self):
        return self.m_discipline

    def event(self):
        return self.m_event

    def h2hScore(self, index, skill, oppSkill):
        return self.transformNumber(self.randWeightedH2H(skill, oppSkill), index)

    def hasValue(self, key):
        return key in self.m_dataPoints

    def individualScore(self, index, skill=None):
        if skill is None:
            return self.transformNumber(self.randUniform(), index)
        else:
            return self.transformNumber(self.randWeighted(skill), index)

    def name(self):
        return self.m_name

    def paradigm(self):
        return self.m_paradigm

    def paradigmOptions(self):
        return dict(self.m_paradigmOptions)

    def randGaussian(self):
        # Box–Muller method
        r1, r2 = self.randUniform(), self.randUniform()
        # randUniform() returns exactly 0.0 whenever the Mersenne Twister
        # yields its minimum value, and log(0) is the same "math domain
        # error" that used to take a scorination down from rand_kumaraswamy()
        r1 = max(r1, 1e-12)
        return math.pow(-2 * math.log(r1), 0.5) * math.cos(2 * math.pi * r2)

    def randGaussianCapped(self, cap):
        rval = self.randGaussian()
        if rval < cap:
            rval = cap
        elif rval > 1 - cap:
            rval = 1 - cap
        return rval

    def rand_kumaraswamy(self, a, b, skew):
        # skew = True: skewed toward 1; False: skewed toward 0
        # both shape parameters must be positive: a non-positive one turns the
        # inner power into a negative exponent on a zero base, which raises
        # "math domain error" and takes the whole scorination down
        a = max(a, 1e-6)
        b = max(b, 1e-6)
        rand = self.randUniform()
        rand = min(max(rand, 0.0), 1.0)
        if skew:
            rval = math.pow(1 - math.pow(1 - rand, 1 / b), 1 / a)
        else:
            rval = 1 - math.pow(1 - math.pow(1 - rand, 1 / a), 1 / b)
        return rval

    def randUniform(self):
        if self.r is not None:
            return (self.r() - self.r.min()) / float(self.r.max() - self.r.min())
        else:
            print("no PRNG set", file=sys.stderr)
            return -1

    def randWeighted(self, skill):
        skill = 0.5 - (1 if 0.5 - skill > 0 else -1) * math.pow(abs(0.5 - skill), 1 / 4.0) / math.pow(2, 3 / 4.0)
        return self.randWeightedFull(skill, 1.4, 2, 4, True)

    def randWeightedH2H(self, skill, oppSkill):
        return self.randWeightedFull(0.5 + (skill - oppSkill) / 2, 1.02, 2.4, 3.8, False)

    def randWeightedFull(self, skill, minConstant, midConstant, maxConstant, skew):
        # the a/b parameterisation below is only meaningful for a normalised
        # skill. A signup list whose min/max don't bracket its entries (say,
        # after the sport is switched to a paradigm that rescales) yields
        # skills well outside it, so pin them rather than produce nonsense.
        scorSkill = min(max(skill, 0.0), 1.0)
        if scorSkill > 0.5:
            a = (scorSkill - 0.5) * 2 * (maxConstant - midConstant) + midConstant
        else:
            a = scorSkill * 2 * (midConstant - minConstant) + minConstant
        if scorSkill < 0.5:
            b = (0.5 - scorSkill) * 2 * (maxConstant - midConstant) + midConstant
        else:
            b = (1 - scorSkill) * (midConstant - minConstant) + minConstant
        return self.rand_kumaraswamy(a, b, skew)

    def scorinator(self):
        return self.m_scorinator

    def setAlphabetizedName(self, name):
        self.m_alphaName = name

    def setDiscipline(self, discipline):
        self.m_discipline = discipline

    def setEvent(self, event):
        self.m_event = event

    def setName(self, name):
        self.m_name = name

    def setParadigm(self, paradigm):
        self.m_paradigm = paradigm

    def setParadigmOptions(self, paradigmOptions):
        self.m_paradigmOptions = paradigmOptions

    def setPRNG(self, newR):
        self.r = newR

    def setScorinator(self, scorinator):
        self.m_scorinator = scorinator

    def transformNumber(self, x, index):
        points = sorted(self.m_dataPoints.get(index, {}).items())
        if len(points) <= 1:  # we can't deal with only one value
            print("m_dataPoints not big enough for index", index,
                  "in XkorSport.transformNumber", file=sys.stderr)
            return -1
        a = b = None
        for j in range(len(points)):
            if j + 1 == len(points):
                # b is j; a is the point before j
                a = points[j - 1]
                b = points[j]
                break
            elif x < points[j + 1][0]:
                a = points[j]
                b = points[j + 1]
                break
        return a[1] + (b[1] - a[1]) / (b[0] - a[0]) * (x - a[0])
