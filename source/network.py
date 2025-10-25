from . import config
from .ieee738 import ConductorParams
import pandas
import pypsa

LINES_FILE=config.LINES_CSV
LOADS_FILE=config.LOADS_CSV
GENS_FILE =config.GENERATORS_CSV
BUSES_FILE=config.BUSES_CSV
TRANS_FILE=config.TRANSFORMERS_CSV
SHUNT_FILE=config.SHUNT_IMPEDANCES_CSV

CDLIB = config.CONDUCTOR_LIBRARY_CSV
CDRAT = config.CONDUCTOR_RATINGS_CSV

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
            self.subnet.add(
                "Bus",
                row["name"],
                bus_name=row["BusName"],
                x=row["x"],
                y=row["y"])
        
        for _, row in self.generators.iterrows():
            self.subnet.add(
                "Generator",
                bus=row["bus"],
                name=row["name"],
                p_nom=row["p_nom"],
                marginal_cost=1)

        for _, row in self.lines.iterrows():
            self.subnet.add(
                "Line",
                name=row["name"],
                bus0=row["bus0"],
                bus1=row["bus1"],
                x=row["x"],
                s_nom=row["s_nom"])

        for _, row in self.loads.iterrows():
            self.subnet.add("Load", **row)

        #for _, row in self.transformers.iterrows():
        #    self.subnet.add("Transformer", **row)
            
        #for _, row in self.shunts.iterrows():
        #    self.subnet.add("ShuntImpedance", **row)
        
    def apply_atmospherics(self, **kwargs):
        params = PartialConductorParams(**kwargs)
        pass

    def solve(self):
        self.subnet.optimize()
        self.subnet.pf()

network = Network()
