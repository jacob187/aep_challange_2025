# N-1 Contingency Analysis Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Streamlit)                      │
│                                                                   │
│  ┌───────────────┐    ┌──────────────────────────────────┐     │
│  │  Main Page    │    │  N-1 Analysis Page (NEW)         │     │
│  │               │    │                                   │     │
│  │ - Dynamic     │    │ - Atmospheric Inputs              │     │
│  │   Rating      │    │ - Component Selection             │     │
│  │ - Stress Map  │    │ - Run Analysis Button             │     │
│  │               │    │ - Results Table                   │     │
│  └───────────────┘    │ - Export CSV                      │     │
│                        └──────────────────────────────────┘     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 │ API Calls
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                        Business Logic Layer                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │            Contingency Class (NEW)                     │     │
│  │                                                         │     │
│  │  + run_n1_analysis(atmos_params, component_types)      │     │
│  │  + _analyze_single_contingency(...)                    │     │
│  │  + get_worst_contingencies(top_n)                      │     │
│  │  + get_contingencies_by_outage(component_name)         │     │
│  │  + export_summary(filepath)                            │     │
│  │                                                         │     │
│  │  - base_network: Network                               │     │
│  │  - contingency_results: DataFrame                      │     │
│  └──────────────────┬──────────────────────────────────────┘     │
│                     │                                             │
│                     │ Uses (composition)                          │
│                     │                                             │
│  ┌──────────────────▼──────────────────────────────────────┐    │
│  │            Network Class (Abstract)                      │    │
│  │                                                           │    │
│  │  + apply_atmospherics(**kwargs) → DataFrame             │    │
│  │  + solve()                                               │    │
│  │  + reset()                                               │    │
│  │  # _create_subnet()                         [Protected] │    │
│  │  # _adjust_s_nom(network, params, line)     [Protected] │    │
│  │  # _calculate_stress(network, line)         [Protected] │    │
│  │  - __adjust_load(load, hour)                [Private]   │    │
│  │                                                           │    │
│  │  - subnet: pypsa.Network                                 │    │
│  │  - conductors: Conductors                                │    │
│  │  - buses, lines, loads, generators, etc.                 │    │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Uses
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                      External Libraries                          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   PyPSA      │  │   IEEE-738   │  │   Pandas     │           │
│  │              │  │              │  │              │           │
│  │ Power Flow   │  │ Thermal      │  │ Data         │           │
│  │ Optimization │  │ Ratings      │  │ Manipulation │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────────────────────────────────────────────────┘
```

## Class Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Network (ABC)                            │
│  Abstract base class for power system networks               │
│                                                              │
│  Purpose: Single-scenario power flow analysis                │
│  Responsibility: Load data, apply conditions, solve, stress  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Inheritance (for concrete impl.)
                        │
        ┌───────────────▼────────────────┐
        │     MyNetwork / TestNetwork    │
        │   (Concrete implementations)   │
        └────────────────────────────────┘
                        │
                        │ Composition (base_network)
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                   Contingency                                 │
│  N-1 Contingency analyzer                                     │
│                                                               │
│  Purpose: Multi-scenario reliability analysis                 │
│  Responsibility: Orchestrate outages, aggregate results       │
└───────────────────────────────────────────────────────────────┘
```

## Data Flow - Single Scenario

```
User Input (atmos_params)
        │
        ▼
┌───────────────────────┐
│ Network.apply_        │
│ atmospherics()        │
└───────┬───────────────┘
        │
        ├─► _adjust_load()        (Modify loads based on time)
        │
        ├─► _adjust_s_nom()       (Calculate dynamic line ratings)
        │        │
        │        └─► IEEE-738 calculations
        │
        ├─► solve()               (PyPSA power flow)
        │
        └─► _calculate_stress()   (Evaluate line loading)
                │
                ▼
        Results DataFrame
```

## Data Flow - N-1 Analysis

```
User Input (atmos_params, component_types)
        │
        ▼
┌──────────────────────────────────────┐
│ Contingency.run_n1_analysis()        │
└────────┬─────────────────────────────┘
         │
         │ For each component in component_types:
         │
         ├─► Get components list (lines, transformers)
         │
         │   For each component:
         │   │
         │   ├─► _analyze_single_contingency()
         │   │        │
         │   │        ├─► copy.deepcopy(base_network)
         │   │        │
         │   │        ├─► Set component.s_nom = 0.001  (outage)
         │   │        │
         │   │        ├─► Apply atmospherics
         │   │        │        │
         │   │        │        └─► _adjust_load()
         │   │        │        └─► _adjust_s_nom()
         │   │        │        └─► solve()
         │   │        │        └─► _calculate_stress()
         │   │        │
         │   │        └─► Collect violations
         │   │                 │
         │   └─────────────────┤
         │                     │
         └─────────────────────┤
                               │
                               ▼
                  Aggregate all violations
                               │
                               ▼
                  Full Results DataFrame
                               │
                               ├─► get_worst_contingencies()
                               ├─► get_contingencies_by_outage()
                               └─► export_summary()
```

## Sequence Diagram - N-1 Analysis

```
User          Frontend      Contingency        Network         PyPSA
 │               │              │                │              │
 │ Click "Run"   │              │                │              │
 ├──────────────►│              │                │              │
 │               │              │                │              │
 │               │ run_n1_      │                │              │
 │               │ analysis()   │                │              │
 │               ├─────────────►│                │              │
 │               │              │                │              │
 │               │              │ For each line: │              │
 │               │              │                │              │
 │               │              │ deepcopy()     │              │
 │               │              ├───────────────►│              │
 │               │              │                │              │
 │               │              │ set s_nom=0    │              │
 │               │              ├───────────────►│              │
 │               │              │                │              │
 │               │              │ apply_         │              │
 │               │              │ atmospherics() │              │
 │               │              ├───────────────►│              │
 │               │              │                │              │
 │               │              │                │ optimize()   │
 │               │              │                ├─────────────►│
 │               │              │                │              │
 │               │              │                │ pf()         │
 │               │              │                ├─────────────►│
 │               │              │                │              │
 │               │              │                │ results      │
 │               │              │                │◄─────────────┤
 │               │              │                │              │
 │               │              │ stress results │              │
 │               │              │◄───────────────┤              │
 │               │              │                │              │
 │               │              │ (Repeat for    │              │
 │               │              │  all lines)    │              │
 │               │              │                │              │
 │               │ DataFrame    │                │              │
 │               │◄─────────────┤                │              │
 │               │              │                │              │
 │ Display Table │              │                │              │
 │◄──────────────┤              │                │              │
 │               │              │                │              │
```

## Method Visibility and Access

```
Network Class:
├── Public Methods
│   ├── apply_atmospherics()    ← Called by user/Contingency
│   ├── solve()                 ← Called by user/Contingency
│   └── reset()                 ← Called by user
│
├── Protected Methods (single _)
│   ├── _create_subnet()        ← Can be overridden by subclass
│   ├── _adjust_s_nom()         ← Called by Contingency
│   └── _calculate_stress()     ← Called by Contingency
│
└── Private Methods (double __)
    └── __adjust_load()         ← Internal only (name mangling)
```

## Design Patterns Used

### 1. Composition over Inheritance

```
Contingency
    └── has-a: base_network (Network)

Rather than:
    Contingency extends Network
```

**Why**: Allows Contingency to work with any Network implementation without tight coupling.

### 2. Strategy Pattern

```
Network (Abstract)
    ├── Strategy: _adjust_s_nom()
    ├── Strategy: _calculate_stress()
    └── Template: apply_atmospherics()
```

**Why**: Different concrete Networks can override calculation strategies.

### 3. Template Method

```
apply_atmospherics():
    1. _adjust_load()
    2. _adjust_s_nom()
    3. solve()
    4. _calculate_stress()
```

**Why**: Ensures consistent workflow while allowing step customization.

## Memory Management

```
Base Network (1x)
    ↓
For each contingency:
    ↓
    Deep Copy (temporary)
        ↓
        Modify (outage)
        ↓
        Solve
        ↓
        Extract results
        ↓
    Delete copy (garbage collected)
```

**Memory usage**: Peak = Base + 1 Copy ≈ 2x base network size

## Performance Characteristics

| Operation         | Complexity        | Time (Hawaii 40) |
| ----------------- | ----------------- | ---------------- |
| Load base network | O(n)              | < 1 second       |
| Single power flow | O(n²)             | ~2 seconds       |
| N-1 analysis      | O(n × n²) = O(n³) | 2-5 minutes      |
| Deep copy         | O(n)              | < 0.1 seconds    |

Where n = number of components (buses, lines, etc.)

## Extension Points

### Future: N-2 Analysis

```
Contingency
    └── run_nk_analysis(k, atmos_params)
            │
            └─► combinations(components, k)
                    │
                    └─► _analyze_k_contingency(outage_list)
```

### Future: Parallel Processing

```
run_n1_analysis()
    │
    └─► multiprocessing.Pool()
            │
            └─► map(_analyze_single_contingency, components)
```

### Future: Time Series Analysis

```
run_n1_timeseries()
    │
    └─► For each timestep:
            │
            └─► run_n1_analysis(atmos_params[t])
```

## File Organization

```
project/
├── source/
│   ├── network.py          ← Base Network class (refactored)
│   ├── contingency.py      ← N-1 Contingency class (NEW)
│   ├── ieee738.py          ← Thermal rating calculations
│   └── config.py           ← Configuration
│
├── docs/
│   ├── AEP_README.md       ← Challenge description
│   ├── CONTINGENCY_ANALYSIS.md    ← Full documentation (NEW)
│   └── N1_ARCHITECTURE.md  ← This file (NEW)
│
├── test_contingency.py     ← Test script (NEW)
├── N1_QUICK_REFERENCE.md   ← Quick ref card (NEW)
└── IMPLEMENTATION_SUMMARY.md ← Implementation notes (NEW)
```

## Summary

The N-1 implementation achieves:

✅ **Separation of Concerns**: Network handles single scenarios, Contingency handles orchestration

✅ **SOLID Principles**: Clean interfaces, single responsibilities, dependency inversion

✅ **Extensibility**: Easy to add N-2, parallel processing, time series

✅ **Maintainability**: Clear architecture, well-documented, tested

✅ **Performance**: Reasonable for hackathon scope (~70 scenarios in 2-5 min)
