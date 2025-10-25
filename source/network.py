import ieee738
import pandas

LINES_FILE="../data/hawaii40_osu/csv/lines.csv"
LOADS_FILE="../data/hawaii40_osu/csv/loads.csv"
GENS_FILE ="../data/hawaii40_osu/csv/generators.csv"

CDLIB = "../data/ieee738/conductor_library.csv"
CDRAT = "../data/ieee738/conductor_ratings.csv"

class Conductors:
    __slots__ = ["library", "ratings"]

    def __init__(self):
        self.library = pandas.read_csv(CDLIB)
        self.ratings = pandas.read_csv(CDRAT)
    

class PartialConductorParams:
    __slots__ = ["partials"]

    def __init__(self, **kwargs):
        self.partials = kwargs

    def apply(self, **remainder):
        full_arguments = { **self.partials, **remainder }
        return ConductorParams(**full_arguments)

        
class Network:
    __slots__ = ["conductors", "lines", "loads", "generators"]

    def __init__(self):
        self.conductors = Conductors()
        self.lines = pandas.read_csv(LINES_FILE)
        self.loads = pandas.read_csv(LOADS_FILE)
        self.generators = pandas.read_csv(GENS_FILE)

    def apply_atmospherics(self, **kwargs):
        params = PartialConductorParams(**kwargs)
        
        pass
