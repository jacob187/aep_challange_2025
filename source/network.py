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

    def find_library(self, name: str):
        for _, conductor in self.library.iterrows():
            if conductor["ConductorName"] == name:
                return conductor
        return None
    
    def find_rating(self, name: str):
        for _, conductor in self.rating.iterrows():
            if conductor["ConductorName"] == name:
                return conductor
        return None
    

class PartialConductorParams:
    __slots__ = ["partials"]

    def __init__(self, **kwargs):
        self.partials = kwargs

    def apply(self, **remainder):
        full_arguments = { **self.partials, **remainder }
        return ieee738.ConductorParams(**full_arguments)

        
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
        self.conductors = Conductors()
        self.buses = pandas.read_csv(BUSES_FILE)
        self.generators = pandas.read_csv(GENS_FILE)
        self.lines = pandas.read_csv(LINES_FILE)
        self.loads = pandas.read_csv(LOADS_FILE)
        self.transformers = pandas.read_csv(TRANS_FILE)
        self.shunts = pandas.read_csv(SHUNT_FILE)
        self.__create_subnet()

    def __create_subnet(self):
        self.subnet = pypsa.Network()
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

    @staticmethod
    def __adjust_s_nom(atmos_params, line):
        conductor = network.conductors.find_library(line["conductor"])
        params = atmos_params.apply(
            Tc=line["MOT"],
            Diameter=conductor["CDRAD_in"] * 2,
            TLo=25,
        RLo=conductor["RES_25C"] / 5280,
        THi=50,
        RHi=conductor["RES_50C"] / 5280)
        
        conductor = ieee738.Conductor(params)
        line["s_nom"] = conductor.steady_state_thermal_rating()
        return line
    
    def apply_atmospherics(self, **kwargs):
        atmos_params = PartialConductorParams(**kwargs)
        self.subnet.lines = self.subnet.lines.apply(
            lambda line : self.__adjust_s_nom(atmos_params, line), axis=1)

    def reset(self):
        self.__create_subnet()
    
    def solve(self):
        self.subnet.optimize()
        self.subnet.pf()

network = Network()
atmospherics = {
    "Ta" : 39,
    "WindVelocity" : 1.0,
    "WindAngleDeg" : 45,
    "Elevation" : 100,
    "Latitude" : 27.0,
    "SunTime" : 12,
    "Emissivity" : 0.5,
    "Absorptivity" : 0.5,
    "Direction" : "EastWest",
    "Atmosphere" : "Clear"
}
