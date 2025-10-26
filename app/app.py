# Path: app/app.py
"""
AEP Dynamic Grid Challenge - Real-Time Analysis Dashboard

A comprehensive Streamlit application for analyzing transmission line stress under
varying atmospheric conditions using IEEE-738 thermal rating calculations.

Features:
- Interactive map visualization with color-coded line stress
- Real-time atmospheric parameter adjustment with sliders
- Line analysis with top N stressed lines
- Conductor comparison charts
- Data export functionality

Usage:
    streamlit run app/app.py

The app uses aggressive caching (@st.cache_resource for Network object) to
ensure fast performance when adjusting parameters.
"""
import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from source.network import Network
from source.config import (
    ONELINE_BUSSES_GEOJSON, 
    ONELINE_LINES_GEOJSON,
    DEFAULT_IEEE738_PARAMS,
    StressLevel,
    STRESS_THRESHOLDS
)

st.set_page_config(layout="wide", page_title="AEP Dynamic Grid Analyzer")

# ============================================================================
# CACHED DATA LOADING
# ============================================================================

@st.cache_resource
def load_network():
    """Load the network once and keep it in memory.
    Use cache_resource for mutable objects that should persist across reruns."""
    return Network()

@st.cache_data
def load_gis_data():
    """Load GIS data for visualization."""
    gis_busses_gdf = gpd.read_file(ONELINE_BUSSES_GEOJSON)
    gis_lines_gdf = gpd.read_file(ONELINE_LINES_GEOJSON)
    return gis_busses_gdf, gis_lines_gdf

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_stress_level(loading_pct):
    """Classify stress level based on loading percentage (0-100+ scale)."""
    if loading_pct < 0.60:
        return "Normal", "green"
    elif loading_pct < 0.90:
        return "Caution", "orange"
    else:
        return "Critical", "red"

def create_line_results_df(network_results: pd.DataFrame, network: Network) -> pd.DataFrame:
    """
    Create a comprehensive DataFrame with line analysis results.
    
    Args:
        network_results: DataFrame from network.apply_atmospherics()
        network: Network object for accessing line metadata
    
    Returns:
        DataFrame with stress analysis and line metadata merged
    """
    # Start with the results from the network calculation
    results_df = network_results.copy()
    
    # Get line metadata - 'name' is the index, not a column!
    lines_meta = network.subnet.lines[['bus0', 'bus1', 'conductor', 'length', 'v_nom']].copy()
    lines_meta['name'] = lines_meta.index  # Add name from index
    
    # Merge on index (both should have same index/order)
    lines_df = pd.concat([lines_meta, results_df], axis=1)
    
    # Verify required columns exist
    required_cols = ['load_percentage']
    missing_cols = [col for col in required_cols if col not in lines_df.columns]
    
    if missing_cols:
        st.warning(f"⚠️ Missing columns: {missing_cols}")
        st.info(f"Available columns in network_results: {results_df.columns.tolist()}")
    
    # Convert load_percentage (0-1 scale) to percent and classify stress
    if 'load_percentage' in lines_df.columns:
        lines_df['loading_pct_display'] = lines_df['load_percentage'] * 100
    else:
        st.warning("⚠️ 'load_percentage' column not found")
        lines_df['loading_pct_display'] = 0
    
    if 'stress_level' not in lines_df.columns or 'stress_color' not in lines_df.columns:
        # Recalculate if missing
        lines_df['stress_level'] = lines_df['load_percentage'].apply(
            lambda x: calculate_stress_level(x)[0] if pd.notna(x) else 'Unknown'
        )
        lines_df['stress_color'] = lines_df['load_percentage'].apply(
            lambda x: calculate_stress_level(x)[1] if pd.notna(x) else 'gray'
        )
    
    return lines_df

def create_interactive_map(lines_df, gis_lines_gdf, gis_busses_gdf):
    """Create an interactive Plotly map with color-coded stress levels."""
    
    # Create lookup dictionary: GIS Name (e.g., 'L0') -> stress data
    # lines_df has 'name' column that should match GIS 'Name'
    name_to_data = {}
    for idx, row in lines_df.iterrows():
        name_to_data[row['name']] = {
            'loading_pct': row['loading_pct_display'],
            'load_a': row['load_a'],
            'rated_capacity': row['rated_capacity'],
            'actual_capacity': row['actual_capacity'],
            'stress_color': row['stress_color'],
            'stress_level': row['stress_level'],
            'at_risk': row['at_risk'],
            'overcapacity': row['overcapacity']
        }
    
    # Calculate center from GIS data (this stays constant)
    centroids = gis_lines_gdf.geometry.centroid
    center_lat = centroids.y.mean()
    center_lon = centroids.x.mean()
    
    fig = go.Figure()
    
    # Add transmission lines with stress color-coding
    for _, row in gis_lines_gdf.iterrows():
        line_name = row['Name']  # e.g., 'L0', 'L1', etc.
        line_data = name_to_data.get(line_name, {})
        
        # Extract stress data
        loading_pct = line_data.get('loading_pct', 0)
        load_a = line_data.get('load_a', 0)
        rated_cap = line_data.get('rated_capacity', 0)
        actual_cap = line_data.get('actual_capacity', 0)
        color = line_data.get('stress_color', 'gray')
        stress_level = line_data.get('stress_level', 'Unknown')
        at_risk = line_data.get('at_risk', False)
        overcap = line_data.get('overcapacity', False)
        
        coords = row.geometry.coords[:]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        # Determine line width based on stress
        line_width = 3 if overcap else 2
        
        # Create informative hover text
        hover_text = (
            f"<b>{row['LineName']}</b><br>"
            f"ID: {line_name}<br>"
            f"Status: <b>{stress_level}</b><br>"
            f"Load: {loading_pct:.1f}%<br>"
            f"Apparent Load: {load_a:.1f} MVA<br>"
            f"Rated Capacity: {rated_cap:.1f} MVA<br>"
            f"Dynamic Capacity: {actual_cap:.1f} MVA<br>"
            f"Voltage: {row['nomkv']} kV<br>"
            f"{'🚨 OVERLOADED' if overcap else ''}"
        )
        
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=lons,
            lat=lats,
            line=dict(width=line_width, color=color),
            hoverinfo="text",
            hovertext=hover_text,
            name=f"Line {line_name}",
            showlegend=False
        ))
    
    # Add buses
    if not gis_busses_gdf.empty:
        fig.add_trace(go.Scattermapbox(
            mode="markers",
            lon=gis_busses_gdf.geometry.x,
            lat=gis_busses_gdf.geometry.y,
            marker=dict(size=8, color="blue", opacity=0.7),
            hoverinfo="text",
            text=gis_busses_gdf['BusName'],
            name="Buses"
        ))
    
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=8.5,
        mapbox_center={"lat": center_lat, "lon": center_lon},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=600,
        title="Hawaii 40-Bus Transmission Grid - Real-Time Stress Analysis"
    )
    
    return fig

def create_conductor_comparison_chart(network, atmos_params):
    """Create a bar chart comparing all conductor types under current conditions."""
    conductor_data = []
    
    for _, conductor in network.conductors.library.iterrows():
        conductor_name = conductor['ConductorName']
        
        # Calculate rating for this conductor at multiple voltages
        for voltage_kv in [69, 138]:
            # Use ieee738 to calculate rating
            from source.ieee738 import Conductor, ConductorParams
            
            params_dict = {
                **atmos_params,
                'Tc': 75,  # Standard MOT
                'Diameter': conductor['CDRAD_in'] * 2,
                'TLo': 25,
                'RLo': conductor['RES_25C'] / 5280,
                'THi': 50,
                'RHi': conductor['RES_50C'] / 5280,
                'Direction': 'EastWest'
            }
            
            cond_params = ConductorParams(**params_dict)
            cond = Conductor(cond_params)
            rating_amps = cond.steady_state_thermal_rating()
            rating_mva = (3**0.5 * rating_amps * voltage_kv * 1000) / 1e6
            
            conductor_data.append({
                'Conductor': conductor_name,
                'Voltage (kV)': voltage_kv,
                'Rating (MVA)': rating_mva
            })
    
    df = pd.DataFrame(conductor_data)
    
    fig = px.bar(
        df,
        x='Conductor',
        y='Rating (MVA)',
        color='Voltage (kV)',
        barmode='group',
        title='Conductor Thermal Ratings Under Current Atmospheric Conditions',
        height=400
    )
    
    return fig

def run_temperature_sensitivity_analysis(network, atmos_params, temp_range):
    """
    Run sensitivity analysis across temperature range, keeping other parameters constant.
    
    Args:
        network: Network object
        atmos_params: Base atmospheric parameters dict
        temp_range: tuple of (min_temp, max_temp, step)
    
    Returns:
        DataFrame with temperature vs line loading data
    """
    min_temp, max_temp, step = temp_range
    
    # Validate step size - recommend at least 1°C for solver stability
    if step < 1.0:
        st.warning(f"⚠️ Step size too small (recommended: 1°C or larger). Using 1°C for stability.")
        step = 1.0
    
    # Generate temperature range
    temps_list = []
    current = min_temp
    while current <= max_temp:
        temps_list.append(current)
        current += step
    
    if len(temps_list) > 50:
        st.warning(f"⚠️ Running {len(temps_list)} scenarios - this may take several minutes.")
    
    sensitivity_data = []
    failed_temps = []
    
    with st.spinner(f"🔄 Running {len(temps_list)} scenarios..."):
        progress_bar = st.progress(0)
        
        for idx, temp in enumerate(temps_list):
            modified_params = atmos_params.copy()
            modified_params['Ta'] = float(temp)
            
            try:
                network.reset()
                results = network.apply_atmospherics(**modified_params)
                
                if results is not None and not results.empty:
                    for line_idx, line_data in results.iterrows():
                        sensitivity_data.append({
                            'Temperature (°C)': temp,
                            'Line': line_idx,
                            'Load %': line_data['load_percentage'] * 100,
                            'Overcapacity': line_data['overcapacity'],
                            'Apparent Load': line_data['load_a'],
                            'Rated Capacity': line_data['rated_capacity'],
                            'Actual Capacity': line_data['actual_capacity']
                        })
            except Exception as e:
                failed_temps.append((temp, str(e)[:50]))
            
            progress_bar.progress((idx + 1) / len(temps_list))
    
    if failed_temps:
        st.info(f"⏭️ Skipped {len(failed_temps)} scenarios due to convergence issues")
    
    return pd.DataFrame(sensitivity_data) if sensitivity_data else None

def create_temperature_sensitivity_chart(sensitivity_df):
    """Create a line chart showing loading percentage vs temperature for each line."""
    fig = px.line(
        sensitivity_df,
        x='Temperature (°C)',
        y='Load %',
        color='Line',
        title='Line Load vs Ambient Temperature',
        labels={'Load %': 'Load Percentage (%)'},
        height=500
    )
    
    # Add critical threshold line
    fig.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Critical (100%)")
    fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Caution (95%)")
    #fig.add_hline(y=80, line_dash="dash", line_color="yellow", annotation_text="Elevated (80%)")
    
    return fig

def create_line_vulnerability_ranking(sensitivity_df):
    """Create a ranking of which lines overload first as temperature increases."""
    # Find the temperature at which each line reaches critical (100%)
    vulnerability_data = []
    
    for line in sensitivity_df['Line'].unique():
        line_df = sensitivity_df[sensitivity_df['Line'] == line].sort_values('Temperature (°C)')
        
        # Find critical temperature
        critical_temps = line_df[line_df['Load %'] >= 100]
        if not critical_temps.empty:
            critical_temp = critical_temps.iloc[0]['Temperature (°C)']
            max_load = line_df['Load %'].max()
        else:
            critical_temp = None
            max_load = line_df['Load %'].max()
        
        vulnerability_data.append({
            'Line': line,
            'Critical Temp (°C)': critical_temp,
            'Max Load %': max_load,
            'Vulnerability': 'CRITICAL' if critical_temp is not None else 'SAFE'
        })
    
    vuln_df = pd.DataFrame(vulnerability_data)
    
    # Sort by critical temperature (None values last)
    vuln_df['sort_key'] = vuln_df['Critical Temp (°C)'].fillna(float('inf'))
    vuln_df = vuln_df.sort_values('sort_key').drop('sort_key', axis=1)
    
    return vuln_df.reset_index(drop=True)

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.title("⚡ AEP Dynamic Grid Challenge - Real-Time Analysis Dashboard")
    st.markdown("### Analyze transmission line stress under varying atmospheric conditions")
    st.markdown("---")
    
    # Load data (cached)
    network = load_network()
    gis_busses_gdf, gis_lines_gdf = load_gis_data()
    
    # ========================================================================
    # SIDEBAR - ATMOSPHERIC CONTROLS
    # ========================================================================
    
    st.sidebar.header("🌤️ Atmospheric Conditions")
    st.sidebar.markdown("Adjust parameters to see real-time impact on grid")
    
    # Ambient Temperature
    Ta = st.sidebar.slider(
        "🌡️ Ambient Temperature (°C)",
        min_value=10.0,
        max_value=50.0,
        value=25.0,
        step=1.0,
        help="Higher temperature reduces line capacity"
    )
    
    # Wind Velocity
    WindVelocity = st.sidebar.slider(
        "💨 Wind Speed (ft/s)",
        min_value=0.0,
        max_value=15.0,
        value=2.0,
        step=0.5,
        help="Higher wind increases convective cooling"
    )
    
    # Wind Angle
    WindAngleDeg = st.sidebar.slider(
        "🧭 Wind Angle (degrees)",
        min_value=0,
        max_value=90,
        value=45,
        step=5,
        help="90° = perpendicular to line (most cooling)"
    )
    
    # Sun Time
    SunTime = st.sidebar.slider(
        "☀️ Time of Day (hour)",
        min_value=0,
        max_value=23,
        value=12,
        step=1,
        help="Affects solar heating on conductors"
    )
    
    # Define these outside expander so they're always available
    Latitude = st.sidebar.number_input("Latitude", value=21.0, step=0.1, key="latitude_input")
    Emissivity = 0.8#st.sidebar.slider("Emissivity", 0.0, 1.0, 0.8, 0.05, key="emissivity_input")
    Absorptivity = 0.8#st.sidebar.slider("Absorptivity", 0.0, 1.0, 0.8, 0.05, key="absorptivity_input")
    Atmosphere = st.sidebar.selectbox("Atmosphere", ["Clear", "Industrial"], key="atmosphere_input")
    Date = st.sidebar.text_input("Date", "12 Jun", key="date_input")
    
    # ========================================================================
    # CALCULATE WITH CURRENT PARAMETERS
    # ========================================================================
    
    # Build atmospherics dictionary
    atmos_params = {
        'Ta': Ta,
        'WindVelocity': WindVelocity,
        'WindAngleDeg': WindAngleDeg,
        'Elevation': 500, # Defaulting elevation to 100 ft
        'Latitude': Latitude,
        'SunTime': SunTime,
        'Emissivity': Emissivity,
        'Absorptivity': Absorptivity,
        'Atmosphere': Atmosphere,
        'Date': Date
    }
    
    # Reset network and apply new atmospherics
    # This recalculates IEEE-738 ratings, runs power flow, and returns stress analysis
    try:
        with st.spinner("🔄 Recalculating line ratings and running power flow..."):
            network.reset()
            # apply_atmospherics now returns the results DataFrame
            network_results = network.apply_atmospherics(**atmos_params)
            
            if network_results is None:
                st.error("⚠️ Network analysis failed - no results returned from apply_atmospherics()")
                st.info("This likely means the power flow did not converge or an error occurred during stress calculation.")
                st.stop()
        
        # Merge network results with line metadata for display
        lines_df = create_line_results_df(network_results, network)
        
        if lines_df is None:
            st.error("⚠️ Failed to process network results into display format")
            st.stop()
    
    except Exception as e:
        st.error(f"⚠️ Error during network analysis: {str(e)}")
        import traceback
        with st.expander("📋 Debug Traceback"):
            st.code(traceback.format_exc())
        st.stop()
    
    # ========================================================================
    # MAIN CONTENT AREA
    # ========================================================================
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Use the actual flags from network analysis
    critical_lines = len(lines_df[lines_df['overcapacity'] == True])
    caution_lines = len(lines_df[(lines_df['load_percentage'] >= 0.95) & (lines_df['load_percentage'] < 1.0)])
    avg_loading = lines_df['load_percentage'].mean() * 100  # Convert to percentage
    max_loading = lines_df['load_percentage'].max() * 100
    avg_capacity = lines_df['actual_capacity'].mean()
    
    col1.metric("🚨 Overloaded Lines", critical_lines, 
                delta=f"{critical_lines} exceed capacity" if critical_lines > 0 else None,
                delta_color="inverse")
    col2.metric("⚡ Avg Capacity", f"{avg_capacity:.1f}MVA")
    col3.metric("📊 Avg Load", f"{avg_loading:.1f}%")
    col4.metric("📈 Max Load", f"{max_loading:.1f}%")
    
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Interactive Map", 
        "📊 Line Analysis", 
        "🔬 Conductor Comparison",
        "📈 Detailed Data",
        "📈 Temperature Sensitivity"
    ])
    
    with tab1:
        st.plotly_chart(
            create_interactive_map(lines_df, gis_lines_gdf, gis_busses_gdf),
            config={"use_container_width": True}
        )
        
        # Legend
        col1, col2, col3 = st.columns(3)
        col1.markdown("🟢 **Normal** (<60%)")
        col2.markdown("🟠 **Caution** (>60%)")
        col3.markdown("🔴 **Critical** (>90%)")
    
    with tab2:
        st.subheader("Top 10 Most Stressed Lines")
        
        top_stressed = lines_df.nlargest(10, 'load_percentage')[
            ['name', 'bus0', 'bus1', 'load_a', 'rated_capacity', 'actual_capacity', 
             'loading_pct_display', 'stress_level', 'overcapacity']
        ].reset_index(drop=True)
        
        # Style the dataframe
        def highlight_stress(row):
            if row['overcapacity']:
                return ['background-color: #880000'] * len(row)
            elif row['loading_pct_display'] >= 90:
                return ['background-color: #883300'] * len(row)
            elif row['loading_pct_display'] >= 60:
                return ['background-color: #444400'] * len(row)
            else:
                return ['background-color: #101010'] * len(row)
        
        st.dataframe(
            top_stressed.style.apply(highlight_stress, axis=1).format({
                'load_a': '{:.2f}',
                'rated_capacity': '{:.2f}',
                'actual_capacity': '{:.2f}',
                'loading_pct_display': '{:.1f}%'
            }),
            width="stretch"
        )
        
        # Add explanation
        st.info("""
        **Key Metrics:**
        - **Load A**: Apparent power flow through the line (MVA)
        - **Rated Capacity**: Static capacity from conductor ratings database
        - **Actual Capacity**: Dynamic capacity calculated via IEEE-738 (changes with weather)
        - **At Risk**: Dynamic capacity exceeds rated capacity (line can handle more than rated, but pushing limits)
        - **Overcapacity**: Actual load exceeds rated capacity (⚠️ overloaded condition)
        """)
        
        # Distribution chart
        fig = px.histogram(
            lines_df,
            x='loading_pct_display',
            nbins=20,
            title='Distribution of Line Load Percentages',
            labels={'loading_pct_display': 'Load (%)'},
            color_discrete_sequence=['steelblue']
        )
        fig.add_vline(x=60, line_dash="dash", line_color="orange", annotation_text="Caution")
        fig.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Critical")
        
        st.plotly_chart(fig, width="stretch")
    
    with tab3:
        st.plotly_chart(
            create_conductor_comparison_chart(network, atmos_params),
            config={"use_container_width": True}
        )
        
        st.info("""
        **💡 Insight:** This chart shows how different conductor types perform under 
        the current atmospheric conditions. Larger conductors generally have higher 
        thermal ratings but may be more expensive to install.
        """)
    
    with tab4:
        st.subheader("Complete Line Data Export")
        
        # Select available columns from the integrated results
        base_cols = ['name', 'bus0', 'bus1', 'conductor', 'length', 'v_nom',
                     'branch_name', 'load_a', 'rated_capacity', 'actual_capacity', 
                     'loading_pct_display', 'stress_level', 'at_risk', 'overcapacity']
        
        available_cols = [col for col in base_cols if col in lines_df.columns]
        
        # Add heat balance components if they exist (from subnet.lines)
        for col in ['Qs', 'Qc', 'Qr']:
            if col in lines_df.columns:
                available_cols.append(col)
        
        # Full data table
        format_dict = {
            'length': '{:.2f}',
            'v_nom': '{:.0f}',
            'load_a': '{:.2f}',
            'rated_capacity': '{:.2f}',
            'actual_capacity': '{:.2f}',
            'loading_pct_display': '{:.1f}%'
        }
        
        # Add formatting for heat balance if present
        if 'Qs' in available_cols:
            format_dict['Qs'] = '{:.2f}'
        if 'Qc' in available_cols:
            format_dict['Qc'] = '{:.2f}'
        if 'Qr' in available_cols:
            format_dict['Qr'] = '{:.2f}'
        
        st.dataframe(
            lines_df[available_cols].style.format(format_dict),
            width="stretch"
        )
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Lines", len(lines_df))
        with col2:
            st.metric("Avg Capacity Utilization", f"{(lines_df['load_a'].sum() / lines_df['rated_capacity'].sum() * 100):.1f}%")
        with col3:
            st.metric("Total System Load", f"{lines_df['load_a'].sum():.1f} MVA")
        
        # Download button
        csv = lines_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Full Data as CSV",
            data=csv,
            file_name=f"grid_analysis_T{Ta}C_Wind{WindVelocity}fps.csv",
            mime="text/csv"
        )
    
    with tab5:
        st.subheader("🌡️ Temperature Sensitivity Analysis")
        st.markdown("""
        **Purpose:** Identify which transmission lines are most vulnerable to temperature increases.
        
        This analysis sweeps through a range of ambient temperatures to determine which lines overload first.
        """)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            min_temp = st.number_input("Min Temp (°C)", value=15.0, step=.1, key="min_t_sens")
        with col2:
            max_temp = st.number_input("Max Temp (°C)", value=50.0, step=0.1, key="max_t_sens")
        with col3:
            step_val = st.number_input("Step (°C)", value=2.0, step=1.0, min_value=1.0, key="step_t_sens", help="Use 1-5°C for stability")
        
        st.caption("💡 Tip: Use 1-5°C temperature steps. Smaller steps may cause solver convergence issues.")
        
        if st.button("▶️ Run Analysis", key="run_sens_btn"):
            sensitivity_df = run_temperature_sensitivity_analysis(network, atmos_params, (min_temp, max_temp, step_val))
            
            if sensitivity_df is not None and not sensitivity_df.empty:
                st.plotly_chart(create_temperature_sensitivity_chart(sensitivity_df), config={"use_container_width": True})
                
                vuln_df = create_line_vulnerability_ranking(sensitivity_df)
                st.subheader("Vulnerability Ranking")
                st.dataframe(vuln_df, width="stretch")
                
                st.info("This analysis helps identify infrastructure priorities.")
            else:
                st.error("Analysis failed")
        else:
            st.info("👆 Click button to run analysis")
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    
    st.markdown("---")
    st.caption("⚡ AEP Transmission Hackathon 2025 | Powered by IEEE-738 & PyPSA")

if __name__ == "__main__":
    main()
