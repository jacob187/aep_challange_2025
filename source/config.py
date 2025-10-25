# Path: src/config.py
"""Configuration and constants for grid analysis"""
from pathlib import Path
from enum import Enum

# Base directory for the project
PROJECT_ROOT = Path(__file__).parent.parent

# Path configurations
DATA_DIR = PROJECT_ROOT / "data"
HAWAII40_OSU_DIR = DATA_DIR / "hawaii40_osu"
HAWAII40_CSV_DIR = HAWAII40_OSU_DIR / "csv"
HAWAII40_GIS_DIR = HAWAII40_OSU_DIR / "gis"
IEEE738_DIR = DATA_DIR / "ieee738"

# Specific CSV and JSON file paths for the Hawaii 40-bus model
BUSES_CSV = HAWAII40_CSV_DIR / "buses.csv"
GENERATORS_CSV = HAWAII40_CSV_DIR / "generators.csv"
LINES_CSV = HAWAII40_CSV_DIR / "lines.csv"
LOADS_CSV = HAWAII40_CSV_DIR / "loads.csv"
GENERATORS_STATUS_CSV = HAWAII40_CSV_DIR / "generators-status.csv"
INVESTMENT_PERIODS_CSV = HAWAII40_CSV_DIR / "investment_periods.csv"
NETWORK_CSV = HAWAII40_CSV_DIR / "network.csv"
SHUNT_IMPEDANCES_CSV = HAWAII40_CSV_DIR / "shunt_impedances.csv"
SNAPSHOTS_CSV = HAWAII40_CSV_DIR / "snapshots.csv"
TRANSFORMERS_CSV = HAWAII40_CSV_DIR / "transformers.csv"
CRS_JSON = HAWAII40_CSV_DIR / "crs.json"
META_JSON = HAWAII40_CSV_DIR / "meta.json"

# Specific Conductor Library and Ratings
CONDUCTOR_LIBRARY_CSV = IEEE738_DIR / "conductor_library.csv"
CONDUCTOR_RATINGS_CSV = IEEE738_DIR / "conductor_ratings.csv"

# GIS GeoJSON files
ONELINE_BUSSES_GEOJSON = HAWAII40_GIS_DIR / "oneline_busses.geojson"
ONELINE_LINES_GEOJSON = HAWAII40_GIS_DIR / "oneline_lines.geojson"


# Grid analysis parameters
class StressLevel(Enum):
    """Classification of line stress"""
    NOMINAL = "Nominal (0-60%)"
    CAUTION = "Caution (60-90%)"
    CRITICAL = "Critical (90-100%)"
    OVERLOADED = "Overloaded (>100%)"

# Ambient condition ranges for analysis
AMBIENT_TEMP_MIN = 15  # °C
AMBIENT_TEMP_MAX = 50  # °C
AMBIENT_TEMP_STEP = 5  # °C

WIND_SPEED_MIN = 0.5  # ft/sec
WIND_SPEED_MAX = 10.0  # ft/sec
WIND_SPEED_STEP = 2.0  # ft/sec

# IEEE738 default parameters (you might want to make some of these dynamic later)
DEFAULT_IEEE738_PARAMS = {
    "WindAngleDeg": 45.0,
    "Elevation": 10.0,  # feet (Hawaii sea level is a reasonable default)
    "Latitude": 21.3,   # Hawaii latitude
    "SunTime": 12.0,    # Noon (peak solar heating)
    "Emissivity": 0.5,
    "Absorptivity": 0.7,
    "Direction": "NorthSouth", # Orientation of conductor
    "Atmosphere": "Clear",
    "Date": "12 Jun",
    "Tc": 75.0, # Max operating temperature, usually from line data
}

# Classification thresholds (as percentage of rating)
STRESS_THRESHOLDS = {
    0: StressLevel.NOMINAL,
    0.6: StressLevel.CAUTION,
    0.9: StressLevel.CRITICAL,
    1.0: StressLevel.OVERLOADED,
}