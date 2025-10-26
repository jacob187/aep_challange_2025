# N-1 Contingency Analysis - Quick Reference

## What is N-1?

N-1 analysis tests grid reliability by simulating the loss of each component one at a time. The system is "N-1 secure" if it can survive any single component failure without overloads.

## Quick Start

### 1. Basic Usage

```python
from source.network import Network
from source.contingency import Contingency

# Create network
class MyNetwork(Network):
    pass

base_network = MyNetwork()

# Create analyzer
contingency = Contingency(base_network)

# Run analysis
results = contingency.run_n1_analysis(
    atmos_params={
        "Temperature": 40,     # °C
        "WindSpeed": 2,        # ft/s
        "WindAngle": 45,       # degrees
        "SunTime": 14          # hour (24-hr format)
    },
    component_types=["Line"]
)

# View results
print(f"Found {len(results)} violations")
print(contingency.get_worst_contingencies(10))
```

### 2. Command Line Test

```bash
python test_contingency.py
```

## Key Concepts

### Atmospheric Conditions (Constant)

During N-1 analysis, these remain **fixed** across all scenarios:

- **Temperature**: Ambient air temperature (°C)
- **WindSpeed**: Wind velocity (ft/s)
- **WindAngle**: Wind direction relative to line (°)
- **SunTime**: Hour of day (0-23)

### What Gets Outaged?

- Each **Line** is removed one at a time
- Each **Transformer** can also be removed (optional)
- System is re-solved after each removal
- Process repeats for all components

### Output Columns

| Column              | Meaning                             |
| ------------------- | ----------------------------------- |
| `outaged_component` | Which component was removed         |
| `affected_branch`   | Which line is now overloaded        |
| `load_percentage`   | How loaded the line is (1.0 = 100%) |
| `overcapacity`      | TRUE if overloaded                  |
| `at_risk`           | TRUE if capacity exceeds rating     |

## Common Use Cases

### Find Worst Contingencies

```python
worst_10 = contingency.get_worst_contingencies(top_n=10)
```

### Analyze Specific Outage

```python
impacts = contingency.get_contingencies_by_outage("LINE_NAME")
```

### Export to CSV

```python
contingency.export_summary("results.csv")
```

### Include Transformers

```python
results = contingency.run_n1_analysis(
    atmos_params=params,
    component_types=["Line", "Transformer"]
)
```

## Interpreting Results

### Loading Levels

- **< 60%**: ✅ Normal operation
- **60-90%**: ⚠️ Caution
- **> 90%**: 🔴 Critical
- **> 100%**: 🚨 Overload

### Status Indicators

- **OVERLOAD**: Load exceeds actual capacity (flow > thermal limit)
- **AT RISK**: Actual capacity exceeds rated capacity (thermal limit > design)

### Example Output

```
Contingency: Loss of Line 'ALOHA138 TO HONOLULU138 CKT 1'
  Affected Branch: ALOHA138 TO HONOLULU138 CKT 2
  Loading: 95%
  Status: 🔴 CRITICAL (not yet overloaded, but close)
```

## Performance Tips

### Typical Times (Hawaii 40 System)

- **Lines only**: ~2-3 minutes (70 scenarios)
- **Lines + Transformers**: ~3-5 minutes (90+ scenarios)

### Speed Up Analysis

1. Start with lines only
2. Filter to critical voltage levels
3. Run during off-peak computing
4. Use caching for repeated analyses

## Troubleshooting

### "Power flow failed"

Some contingencies may not converge (system becomes unstable):

- **Normal**: Indicates a critical contingency
- **Logged**: Error message captured in results
- **Analysis continues**: Other contingencies still run

### "No violations found"

System is N-1 secure under these conditions:

- ✅ Good news!
- Try more extreme conditions (higher temp, lower wind)

### Memory issues

If running out of memory:

- Analyze fewer components at once
- Close other applications
- Reduce system size if testing

## Integration with Main App

### Recommended UI Layout

```
Main Page
├── Dynamic Rating Analysis
└── [Existing features]

N-1 Analysis Page (NEW)
├── Atmospheric Inputs
│   ├── Temperature slider
│   ├── Wind speed slider
│   ├── Wind angle slider
│   └── Time of day slider
├── Options
│   ├── ☐ Analyze Lines
│   └── ☐ Analyze Transformers
├── [Run N-1 Analysis] button
└── Results
    ├── Summary stats
    ├── Violations table
    └── [Export CSV] button
```

### Streamlit Caching

```python
@st.cache_resource
def get_contingency_analyzer():
    return Contingency(MyNetwork())

# Use in app
contingency = get_contingency_analyzer()
```

## Key Files

- **Implementation**: `source/contingency.py`
- **Test Script**: `test_contingency.py`
- **Documentation**: `docs/CONTINGENCY_ANALYSIS.md`
- **Summary**: `IMPLEMENTATION_SUMMARY.md`

## Questions?

See full documentation in `docs/CONTINGENCY_ANALYSIS.md`

---

**Remember**: N-1 analysis answers "What happens if we lose X?" under specific environmental conditions. It's a snapshot of system reliability at a particular moment in time.
