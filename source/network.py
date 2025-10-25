import ieee738
import pandas
import pypsa

LINES_FILE="../data/hawaii40_osu/csv/lines.csv"
LOADS_FILE="../data/hawaii40_osu/csv/loads.csv"
GENS_FILE ="../data/hawaii40_osu/csv/generators.csv"
BUSES_FILE="../data/hawaii40_osu/csv/buses.csv"
TRANS_FILE="../data/hawaii40_osu/csv/transformers.csv"
SHUNT_FILE="../data/hawaii40_osu/csv/shunt_impedances.csv"

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
    __slots__ = [
        "subnet",
        "conductors",
        "buses",
        "lines",
        "loads",
        "generators",
        "transformers",
        "shunts"
    ]

    def __init__(self):
        self.subnet = pypsa.Network()
        self.conductors = Conductors()
        self.buses = pandas.read_csv(BUSES_FILE)
        self.generators = pandas.read_csv(GENS_FILE)
        self.lines = pandas.read_csv(LINES_FILE)
        self.loads = pandas.read_csv(LOADS_FILE)
        self.transformers = pandas.read_csv(TRANS_FILE)
        self.shunts = pandas.read_csv(SHUNT_FILE)
        self.__load_subnet()

    def __load_subnet(self):
        for _, row in self.buses.iterrows():
            self.subnet.add("Bus", **(row.to_dict()))
        
        for _, row in self.generators.iterrows():
            row["marginal_cost"] = 1
            self.subnet.add("Generator", **(row.to_dict()))

        for _, row in self.lines.iterrows():
            self.subnet.add("Line", **(row.to_dict()))

        for _, row in self.loads.iterrows():
            self.subnet.add("Load", **(row.to_dict()))

        for _, row in self.transformers.iterrows():
            self.subnet.add("Transformer", **row)
            
        for _, row in self.shunts.iterrows():
            self.subnet.add("ShuntImpedance", **row)
        
    def apply_atmospherics(self, **kwargs):
        params = PartialConductorParams(**kwargs)
        pass

    def solve(self):
        self.subnet.optimize()
        self.subnet.pf()

network = Network()
