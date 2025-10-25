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

    def find_library(self, name):
        for _, conductor in self.library.iterrows():
            if conductor["ConductorName"] == name:
                return conductor
        return None
    
    def find_rating(self, name, mot):
        for _, conductor in self.rating.iterrows():
            if conductor["ConductorName"] == name and conductor["MOT"] == mot:
                return conductor
        return None
    

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

    def find_bus(self, name):
        for _, row in self.buses.iterrows():
            if row["name"] == int(name):
                return row
        return None
            
    @staticmethod
    def __adjust_s_nom(network, atmos_params, line):
        conductor = network.conductors.find_library(line["conductor"])
        bus0 = network.find_bus(line["bus0"])
        bus1 = network.find_bus(line["bus1"])

        assert bus0["v_nom"] == bus1["v_nom"]
        x_diff = abs(bus0["x"] - bus0["y"])
        y_diff = abs(bus0["y"] - bus1["y"])
        v_nom = float(bus0["v_nom"])
        if x_diff > y_diff:
            direction = "EastWest"
        else:
            direction = "NorthSouth"
        
        params = atmos_params.apply(
            Direction=direction,
            Tc=line["MOT"],
            Diameter=conductor["CDRAD_in"] * 2,
            TLo=25,
            RLo=conductor["RES_25C"] / 5280,
            THi=50,
            RHi=conductor["RES_50C"] / 5280)
        
        conductor = ieee738.Conductor(params)
        I = conductor.steady_state_thermal_rating()
        Ikv = 3**0.5 * I * (v_nom * 1000)  / 1e6
        line["s_nom"] = Ikv
        line["Qs"] = conductor.qs
        line["Qc"] = conductor.qc
        line["Qr"] = conductor.qr
        return line
    
    def apply_atmospherics(self, **kwargs):
        atmos_params = PartialConductorParams(**kwargs)
        self.subnet.lines = self.subnet.lines.apply(
            lambda line : self.__adjust_s_nom(self, atmos_params, line), axis=1)

    def reset(self):
        self.__create_subnet()
    
    def solve(self):
        self.subnet.optimize()
        self.subnet.pf()

network = Network()
atmospherics = {
    "Ta" : 28,
    "WindVelocity" : 1.0,
    "WindAngleDeg" : 30,
    "Elevation" : 100,
    "Latitude" : 11.0,
    "SunTime" : 12,
    "Emissivity" : 0.8,
    "Absorptivity" : 0.8,
    "Direction" : "EastWest",
    "Atmosphere" : "Clear"
}
ambient_defaults = {
    'Ta': 25,
    'WindVelocity': 2.0, 
    'WindAngleDeg': 90,
    'SunTime': 12,
    'Elevation': 1000,
    'Latitude': 27,
    'SunTime': 12,
    'Emissivity': 0.8,
    'Absorptivity': 0.8,
    'Direction': 'EastWest',
    'Atmosphere': 'Clear',
    'Date': '12 Jun',
}
