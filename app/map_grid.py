import streamlit as st
import geopandas as gpd
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add the project root to Python's path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.config as config

@st.cache_data
def load_gis_data():
    """Load GIS data for buses and lines."""
    gis_busses_gdf = gpd.read_file(config.ONELINE_BUSSES_GEOJSON)
    gis_lines_gdf = gpd.read_file(config.ONELINE_LINES_GEOJSON)
    return gis_busses_gdf, gis_lines_gdf

def display_hawaii_map():
    gis_busses_gdf, gis_lines_gdf = load_gis_data()

    # Center the map on Honolulu
    center_lat = 21.4569
    center_lon = -157.87583

    # Create Plotly figure
    fig = go.Figure()

    # Add transmission lines
    if not gis_lines_gdf.empty:
        for idx, row in gis_lines_gdf.iterrows():
            line_coords = row.geometry.coords
            lons = [c[0] for c in line_coords]
            lats = [c[1] for c in line_coords]
            
            # Access 'LineName' from the GeoJSON properties
            line_name = row.get('LineName', f"Line {idx}")

            fig.add_trace(go.Scattermapbox(
                mode="lines",
                lon=lons,
                lat=lats,
                line=dict(width=2, color="gray"),
                hoverinfo="text",
                text=f"{line_name}",
                name=line_name,
                showlegend=False
            ))

    # Add buses as markers
    if not gis_busses_gdf.empty:
        fig.add_trace(go.Scattermapbox(
            mode="markers",
            lon=gis_busses_gdf.geometry.x,
            lat=gis_busses_gdf.geometry.y,
            marker=dict(size=8, color="blue", opacity=0.7),
            hoverinfo="text",
            # Access 'BusName' from the GeoJSON properties
            text=gis_busses_gdf['BusName'],
            name="Buses"
        ))

    # Update layout
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=9, # Increased zoom level to focus more on Oahu
        mapbox_center={"lat": center_lat, "lon": center_lon},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=700,
        title="Hawaii 40-Bus Transmission Grid (Oahu)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.write(f"**Loaded {len(gis_lines_gdf)} transmission lines**")
    st.write(f"**Loaded {len(gis_busses_gdf)} buses**")
