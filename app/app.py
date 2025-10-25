import streamlit as st
import geopandas as gpd
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add the project root to Python's path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.config as config
import app.map_grid as map_grid
import app.evaluate_network as evaluate_network

st.set_page_config(layout="wide", page_title="AEP Grid Layout")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Transmission Grid Visualization", "Bus Locations", "Network Evaluation"])

if page == "Transmission Grid Visualization":
    st.subheader("Transmission Grid Visualization")
    st.write("Interactive map of transmission lines and buses loaded from GeoJSON files.")
    map_grid.display_hawaii_map()
elif page == "Bus Locations":
    st.subheader("Bus Locations")
    st.write("Displaying bus locations.")
    gis_busses_gdf, _ = map_grid.load_gis_data()
    st.dataframe(gis_busses_gdf)

elif page == "Network Evaluation":
    st.subheader("Network Evaluation")
    st.write("Evaluating the network.")
    evaluate_network.evaluate_network()