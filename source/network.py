from . import config
from . import ieee738
import pandas
import pypsa
from math import pi, sin

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
        for _, conductor in self.ratings.iterrows():
            if conductor["ConductorName"] == name and conductor["MOT"] == mot:
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
        "shunts",
        "results"
    ]

    def __init__(self):
        self.conductors = Conductors()
        self.buses = pandas.read_csv(BUSES_FILE)
        self.generators = pandas.read_csv(GENS_FILE)
        self.lines = pandas.read_csv(LINES_FILE)
        self.loads = pandas.read_csv(LOADS_FILE)
        self.transformers = pandas.read_csv(TRANS_FILE)
        self.shunts = pandas.read_csv(SHUNT_FILE)
        self.results = list()
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
        self.loads = self.subnet.loads

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
        line["v_nom"] = v_nom
        line["Qs"] = conductor.qs
        line["Qc"] = conductor.qc
        line["Qr"] = conductor.qr
        return line

    @staticmethod
    def __calculate_stress(network, line):
        s_nom   = line["s_nom"]
        v_nom   = line["v_nom"]
        ratings = network.conductors.find_rating(line["conductor"], line["MOT"])
        
        load_a  = abs(network.subnet.lines_t["p0"][line.name]["now"])
        cap     = ratings["RatingMVA_69"] if int(v_nom) == 69 else ratings["RatingMVA_138"]
        at_risk = s_nom > cap
        overcap = load_a > cap
        load    = load_a / cap

        result = {
            "branch_name"     : line["branch_name"],
            "load_a"          : load_a,
            "rated_capacity"  : cap,
            "actual_capacity" : s_nom,
            "at_risk"         : at_risk,
            "overcapacity"    : overcap,
            "load_percentage" : load
        }
        return result

    @staticmethod
    def __adjust_load(load, hour_of_day):
        assert config.MINIMUM_LOAD_TIME < config.MAXIMUM_LOAD_TIME
        offset = config.MAXIMUM_LOAD_TIME - config.MINIMUM_LOAD_TIME
        angle = ((hour_of_day - offset) / 24)\
            * 2 * pi
        p_set_n = load["p_set"] + (load["p_set"] * sin(angle) * config.LOAD_VARIANCE)
        load["p_set"] = p_set_n
        return load
    
    def apply_atmospherics(self, **kwargs):
        atmos_params = PartialConductorParams(**kwargs)
        self.subnet.loads = self.loads.apply(
            lambda load : self.__adjust_load(load, kwargs["SunTime"]), axis=1)
        self.subnet.lines = self.subnet.lines.apply(
            lambda line : self.__adjust_s_nom(self, atmos_params, line), axis=1)
        self.solve()
        self.results = self.subnet.lines.apply(
            lambda line : self.__calculate_stress(self, line), axis=1, result_type="expand")
        return self.results

    def reset(self):
        self.__create_subnet()
    
    def solve(self):
        self.subnet.optimize()
        self.subnet.pf()
