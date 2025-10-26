# N-1 Contingency Analysis

## Overview

The N-1 Contingency Analysis feature evaluates the power system's reliability by simulating the loss of individual transmission lines or transformers. This "bonus" feature from the AEP challenge helps identify system weaknesses and potential cascading failures under various environmental conditions.

## What is N-1 Analysis?

**N-1** refers to a reliability criterion where the system must continue to operate safely even if any single component (N-1) fails. The analysis:

1. Takes a **base case** power system
2. Holds **atmospheric conditions constant** (temperature, wind speed, time of day)
3. Systematically removes **each component** one at a time
4. Solves the **power flow** for each scenario
5. Identifies **overloads** and **at-risk** conditions

## Architecture

### Class Structure

```
Network (ABC)
    ├── _create_subnet()      # Protected: creates PyPSA network
    ├── _adjust_s_nom()       # Protected: calculates dynamic line ratings
    ├── _calculate_stress()   # Protected: evaluates line loading
    └── apply_atmospherics()  # Public: applies conditions and solves

Contingency
    ├── base_network          # Reference to base Network instance
    ├── run_n1_analysis()     # Main method: performs N-1 analysis
    ├── _analyze_single_contingency()  # Internal: handles one outage
    ├── get_worst_contingencies()      # Helper: returns top N issues
    └── export_summary()      # Helper: exports results to CSV
```

### Design Principles

This implementation follows **SOLID** principles:

- **Single Responsibility**: `Network` handles power flow, `Contingency` handles contingency orchestration
- **Open/Closed**: Base `Network` class is protected methods allow extension without modification
- **Dependency Inversion**: `Contingency` depends on the abstract `Network` interface

## Usage

### Basic Example

```python
from source.network import Network
from source.contingency import Contingency

# Create concrete Network implementation
class MyNetwork(Network):
    pass

# Initialize base network
base_network = MyNetwork()

# Define constant atmospheric conditions
atmos_params = {
    "Temperature": 40,    # 40°C
    "WindSpeed": 2,       # 2 ft/s
    "WindAngle": 45,      # 45°
    "SunTime": 14         # 2 PM
}

# Create contingency analyzer
contingency = Contingency(base_network)

# Run N-1 analysis on all lines
results = contingency.run_n1_analysis(
    atmos_params=atmos_params,
    component_types=["Line"]
)

# View worst contingencies
worst = contingency.get_worst_contingencies(top_n=10)
print(worst)

# Export to CSV
contingency.export_summary("results.csv")
```

### Analyzing Specific Outages

```python
# Get all impacts from losing a specific line
line_impacts = contingency.get_contingencies_by_outage("ALOHA138 TO HONOLULU138 CKT 1")
print(line_impacts)
```

### Including Transformers

```python
# Analyze both lines and transformers
results = contingency.run_n1_analysis(
    atmos_params=atmos_params,
    component_types=["Line", "Transformer"]
)
```

## Output Format

The `run_n1_analysis()` method returns a DataFrame with the following columns:

| Column                   | Type  | Description                                 |
| ------------------------ | ----- | ------------------------------------------- |
| `outaged_component`      | str   | Name/ID of the component that was removed   |
| `outaged_component_type` | str   | Type of component ("Line" or "Transformer") |
| `affected_branch`        | str   | Name of the branch showing issues           |
| `load_a`                 | float | Apparent load in MVA                        |
| `rated_capacity`         | float | Rated capacity in MVA                       |
| `actual_capacity`        | float | Actual capacity under conditions in MVA     |
| `at_risk`                | bool  | True if actual capacity > rated capacity    |
| `overcapacity`           | bool  | True if load > actual capacity              |
| `load_percentage`        | float | Load as fraction of actual capacity (0-1+)  |

### Example Output

```
For loss of "ALOHA138 TO HONOLULU138 CKT 1"

Rating Issues:
"ALOHA138 TO HONOLULU138 CKT 2" 95%

For loss of "FLOWER69 TO HONOLULU69 CKT 1"

Rating Issues:
"FLOWER69 TO HONOLULU69 CKT 2" 92%
"SURF69 TO TURTLE69 CKT 1" 84%
"SURF69 TO COCONUT69 CKT 1" 81%
```

## Performance Considerations

### Computational Complexity

- **N-1 Analysis**: For a system with `n` components, performs `n` power flow calculations
- **Hawaii 40 System**: ~70 lines → ~70 scenarios (~2-5 minutes on typical hardware)

### Optimization Tips

1. **Start with Lines Only**: Analyze only lines first, add transformers if time permits
2. **Filter by Voltage Level**: Focus on critical voltage levels (e.g., 138 kV)
3. **Parallel Processing**: (Future enhancement) Run contingencies in parallel
4. **Caching**: Cache the base case atmospheric calculations

### N-k Analysis (Future Work)

For N-2 or higher (`k > 1`):

- **N-2**: `n choose 2` = `n*(n-1)/2` scenarios (for 70 lines: 2,415 scenarios)
- **N-3**: `n choose 3` = `n*(n-1)*(n-2)/6` scenarios (for 70 lines: 54,740 scenarios)

These are computationally expensive and beyond the scope of a 24-hour hackathon but are architecturally supported by extending the `Contingency` class.

## Integration with Frontend

### Recommended UI Flow

1. **New Tab**: "N-1 Contingency Analysis"
2. **Inputs**:
   - Atmospheric conditions (same as main analysis)
   - Component types to analyze (checkboxes: Lines, Transformers)
   - Optional: Top N results to display
3. **Run Button**: "Run N-1 Analysis"
4. **Output**:
   - Summary statistics (total contingencies, issues found)
   - Table of worst contingencies
   - Option to export to CSV
   - (Optional) Map visualization of affected lines

### Caching Strategy

```python
# In app.py
@st.cache_resource
def get_contingency_analyzer():
    base_network = MyNetwork()
    return Contingency(base_network)

# Usage
contingency = get_contingency_analyzer()
results = contingency.run_n1_analysis(atmos_params)
```

## Testing

Run the test script:

```bash
python test_contingency.py
```

This will:

1. Load the Hawaii 40 bus system
2. Run N-1 analysis at 40°C, 2 PM
3. Display the top 10 worst contingencies
4. Export results to `n1_contingency_results.csv`

## References

- AEP Challenge: `docs/AEP_README.md` (Bonus section)
- Network Module: `source/network.py`
- Contingency Module: `source/contingency.py`
- PyPSA Documentation: https://pypsa.readthedocs.io/

## Future Enhancements

1. **N-k Analysis**: Generalize to handle k > 1 simultaneous outages
2. **Parallel Processing**: Use multiprocessing to speed up analysis
3. **Scenario Filtering**: Pre-filter unlikely scenarios (e.g., radial lines)
4. **Remedial Actions**: Suggest operator actions to mitigate violations
5. **Temporal Analysis**: Run N-1 across multiple time snapshots
6. **Voltage Analysis**: Include voltage violations in addition to thermal
