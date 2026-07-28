from .archeryparadigm import XkorArcheryParadigm
from .autoracingparadigm import XkorAutoRacingParadigm
from .bestofparadigm import XkorBestOfParadigm
from .eliminationraceparadigm import XkorEliminationRaceParadigm
from .fencingparadigm import XkorFencingParadigm
from .footba11erparadigm import XkorFootba11erParadigm
from .golfinatorparadigm import XkorGolfinatorParadigm
from .h2hparadigm import XkorH2HParadigm
from .highjumpparadigm import XkorHighJumpParadigm
from .howzzatparadigm import XkorHowzzatParadigm
from .lisaparadigm import XkorLISAParadigm
from .nsfsparadigm import XkorNSFSParadigm
from .nsfsbaseballparadigm import XkorNSFSBaseballParadigm
from .nsfsgridironparadigm import XkorNSFSGridironParadigm
from .ordinalparadigm import XkorOrdinalParadigm
from .pgsparadigm import XkorPGSParadigm
from .pointsraceparadigm import XkorPointsRaceParadigm
from .progressivethrowparadigm import XkorProgressiveThrowParadigm
from .scoredparadigm import XkorScoredParadigm
from .scorinatorparadigm import XkorScorinatorParadigm
from .shootingparadigm import XkorShootingParadigm
from .shorttrackparadigm import XkorShortTrackParadigm
from .sqisparadigm import XkorSQISParadigm
from .tennisparadigm import XkorTennisParadigm
from .timedparadigm import XkorTimedParadigm
from .wrestlingparadigm import XkorWrestlingParadigm


class XkorParadigmFactory:
    @staticmethod
    def newParadigm(type):
        if type == "archery":
            rval = XkorArcheryParadigm()
        elif type == "autoracing":
            rval = XkorAutoRacingParadigm()
        elif type == "bestof":
            rval = XkorBestOfParadigm()
        elif type == "eliminationrace":
            rval = XkorEliminationRaceParadigm()
        elif type == "fencing":
            rval = XkorFencingParadigm()
        elif type == "footba11er":
            rval = XkorFootba11erParadigm()
        elif type == "golfinator":
            rval = XkorGolfinatorParadigm()
        elif type == "highjump":
            rval = XkorHighJumpParadigm()
        elif type == "howzzat":
            rval = XkorHowzzatParadigm()
        elif type == "lisa":
            rval = XkorLISAParadigm()
        elif type == "nsfs":
            rval = XkorNSFSParadigm()
        elif type == "nsfs-baseball":
            rval = XkorNSFSBaseballParadigm()
        elif type == "nsfs-gridiron":
            rval = XkorNSFSGridironParadigm()
        elif type == "ordinal":
            rval = XkorOrdinalParadigm()
        elif type == "pgs":
            rval = XkorPGSParadigm()
        elif type == "pointsrace":
            rval = XkorPointsRaceParadigm()
        elif type == "progressivethrow":
            rval = XkorProgressiveThrowParadigm()
        elif type == "scored":
            rval = XkorScoredParadigm()
        elif type == "scorinator":
            rval = XkorScorinatorParadigm()
        elif type == "shooting":
            rval = XkorShootingParadigm()
        elif type == "shorttrack":
            rval = XkorShortTrackParadigm()
        elif type == "sqis":
            rval = XkorSQISParadigm()
        elif type == "tennis":
            rval = XkorTennisParadigm()
        elif type == "timed":
            rval = XkorTimedParadigm()
        elif type == "wrestling":
            rval = XkorWrestlingParadigm()
        elif type == "xkoranate-h2h":
            rval = XkorH2HParadigm()
        else:
            rval = XkorTimedParadigm()
        return rval

    @staticmethod
    def newParadigmForSport(s, userOpts):
        """C++ overload XkorParadigmFactory::newParadigm(XkorSport *,
        QHash<QString, QVariant>) — renamed because Python cannot overload on
        argument type."""
        type = s.paradigm()
        rval = XkorParadigmFactory.newParadigm(type)
        rval.init(s, userOpts)
        return rval
