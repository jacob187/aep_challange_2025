from source.network import Network, PartialConductorParams
import pandas as pd
import copy
from typing import Dict, List, Optional


class Contingency:
    """
    Handles N-1 contingency analysis for power systems.
    
    Example flow: 
```
    For loss of "ALOHA138 TO HONOLULU138 CKT 1"

    Ratings Issues:
    "ALOHA138 TO HONOLULU138 CKT 2" 95% 


    For loss of "FLOWER69 TO HONOLULU69  CKT 1"

    Ratings Issues:
    "FLOWER69 TO HONOLULU69  CKT 2" 92% 
    "SURF69 TO TURTLE69 CKT 1" 84%
    "SURF69 TO COCONUT69 CKT 1" 81%
    """
    
    __slots__ = ["base_network", "contingency_results"]

    def __init__(self, base_network: Network):
        """
        Initialize the Contingency analyzer with a base network.
        
        Args:
            base_network: An instance of Network representing the base case
        """
        self.base_network = base_network
        self.contingency_results = None
    
    def analyze_line_outage(self, line_name: str, atmos_params: Dict) -> List[Dict]:
        """
        Analyze the impact of a single line outage.
        
        Args:
            line_name: Name/ID of the line to outage
            atmos_params: Atmospheric parameters for the analysis
        
        Returns:
            List of dictionaries containing results for branches with issues
        """
        return self._analyze_single_contingency(
            component_type="Line",
            component_name=line_name,
            atmos_params=atmos_params
        )

    def run_n1_analysis(self, atmos_params: Dict, component_types: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Perform N-1 contingency analysis on the network.
        
        This method simulates the loss of each transmission line (and optionally
        transformers) one at a time, holding atmospheric conditions constant.
        For each outage, it recalculates power flow and identifies any overloads
        or at-risk conditions.
        
        Args:
            atmos_params: Dictionary of atmospheric parameters (Temperature, WindSpeed, etc.)
                         These conditions remain constant across all contingencies.
            component_types: List of component types to analyze. Defaults to ["Line"].
                           Can include ["Line", "Transformer"].
        
        Returns:
            DataFrame containing contingency results with columns:
                - outaged_component: Name of the component that was outaged
                - outaged_component_type: Type of component (Line/Transformer)
                - affected_branch: Name of branch showing issues
                - load_a: Apparent load in MVA
                - rated_capacity: Rated capacity in MVA
                - actual_capacity: Actual capacity under current conditions in MVA
                - at_risk: Boolean indicating if actual capacity exceeds rated
                - overcapacity: Boolean indicating if load exceeds actual capacity
                - load_percentage: Load as percentage of actual capacity
        
        Example:
            >>> contingency = Contingency(my_network)
            >>> results = contingency.run_n1_analysis({
            ...     "Temperature": 40,
            ...     "WindSpeed": 2,
            ...     "WindAngle": 45,
            ...     "SunTime": 14
            ... })
        """
        if component_types is None:
            component_types = ["Line"]
        
        all_contingency_results = []
        
        # Analyze each component type
        for component_type in component_types:
            print(f"\n{'='*60}")
            print(f"Running N-1 analysis for {component_type}s")
            print(f"{'='*60}")
            
            if component_type == "Line":
                components = self.base_network.subnet.lines
            elif component_type == "Transformer":
                components = self.base_network.subnet.transformers
            else:
                print(f"Warning: Unsupported component type '{component_type}', skipping...")
                continue
            
            # Iterate through each component for N-1 analysis
            total_components = len(components)
            for idx, (component_name, component_data) in enumerate(components.iterrows(), 1):
                print(f"\nContingency {idx}/{total_components}: Outage of {component_type} '{component_name}'")
                
                # Perform contingency analysis for this component
                results = self._analyze_single_contingency(
                    component_type=component_type,
                    component_name=component_name,
                    atmos_params=atmos_params
                )
                
                # Add results if any issues were found
                if results:
                    all_contingency_results.extend(results)
        
        # Convert to DataFrame
        self.contingency_results = pd.DataFrame(all_contingency_results)
        
        # Summary statistics
        if len(self.contingency_results) > 0:
            print(f"\n{'='*60}")
            print(f"N-1 Analysis Summary")
            print(f"{'='*60}")
            print(f"Total contingencies analyzed: {idx if 'idx' in locals() else 0}")
            print(f"Contingencies with issues: {self.contingency_results['outaged_component'].nunique()}")
            print(f"Total affected branches: {len(self.contingency_results)}")
            print(f"Branches with overloads: {self.contingency_results['overcapacity'].sum()}")
            print(f"Branches at risk: {self.contingency_results['at_risk'].sum()}")
        else:
            print(f"\n{'='*60}")
            print("No N-1 violations found - system is N-1 secure!")
            print(f"{'='*60}")
        
        return self.contingency_results

    def _analyze_single_contingency(
        self, 
        component_type: str, 
        component_name: str, 
        atmos_params: Dict
    ) -> List[Dict]:
        """
        Analyze a single contingency scenario.
        
        Args:
            component_type: Type of component to outage ("Line" or "Transformer")
            component_name: Name/ID of the component to outage
            atmos_params: Atmospheric parameters for the analysis
        
        Returns:
            List of dictionaries containing results for branches with issues
        """
        # Create a deep copy of the base network for this contingency
        contingency_network = copy.deepcopy(self.base_network)
        
        try:
            # Take the component out of service by setting active to False
            # This is PyPSA's recommended way to disable components for contingency analysis
            if component_type == "Line":
                contingency_network.subnet.lines.loc[component_name, "active"] = False
            elif component_type == "Transformer":
                contingency_network.subnet.transformers.loc[component_name, "active"] = False
            
            # Apply atmospheric conditions and solve power flow
            atmos_params_obj = PartialConductorParams(**atmos_params)
            
            # Adjust loads based on time of day
            contingency_network.subnet.loads = contingency_network.loads.apply(
                lambda load: contingency_network._Network__adjust_load(load, atmos_params["SunTime"]), 
                axis=1
            )
            
            # Adjust line ratings based on atmospheric conditions
            contingency_network.subnet.lines = contingency_network.subnet.lines.apply(
                lambda line: contingency_network._adjust_s_nom(contingency_network, atmos_params_obj, line), 
                axis=1
            )
            
            # Solve the power flow
            contingency_network.solve()
            
            # Calculate stress on all lines
            stress_results = contingency_network.subnet.lines.apply(
                lambda line: contingency_network._calculate_stress(contingency_network, line), 
                axis=1, 
                result_type="expand"
            )
            
            # Collect results for lines with issues (overcapacity or at_risk)
            issues = []
            for _, line_result in stress_results.iterrows():
                if line_result["overcapacity"] or line_result["at_risk"]:
                    issues.append({
                        "outaged_component": component_name,
                        "outaged_component_type": component_type,
                        "affected_branch": line_result["branch_name"],
                        "load_a": line_result["load_a"],
                        "rated_capacity": line_result["rated_capacity"],
                        "actual_capacity": line_result["actual_capacity"],
                        "at_risk": line_result["at_risk"],
                        "overcapacity": line_result["overcapacity"],
                        "load_percentage": line_result["load_percentage"]
                    })
            
            # Report findings for this contingency
            if issues:
                print(f"  ⚠️  Found {len(issues)} issue(s):")
                for issue in issues:
                    status = "OVERLOAD" if issue["overcapacity"] else "AT RISK"
                    print(f"     - {issue['affected_branch']}: {issue['load_percentage']*100:.1f}% ({status})")
            else:
                print(f"  ✓  No issues")
            
            return issues
            
        except Exception as e:
            print(f"  ❌ Power flow failed: {str(e)}")
            # Log the failure but continue with other contingencies
            return [{
                "outaged_component": component_name,
                "outaged_component_type": component_type,
                "affected_branch": "POWER_FLOW_FAILED",
                "load_a": None,
                "rated_capacity": None,
                "actual_capacity": None,
                "at_risk": False,
                "overcapacity": False,
                "load_percentage": None,
                "error": str(e)
            }]

    def get_worst_contingencies(self, top_n: int = 10) -> pd.DataFrame:
        """
        Get the worst N-1 contingencies based on load percentage.
        
        Args:
            top_n: Number of worst contingencies to return
        
        Returns:
            DataFrame of worst contingencies sorted by load_percentage
        """
        if self.contingency_results is None or len(self.contingency_results) == 0:
            print("No contingency results available. Run run_n1_analysis() first.")
            return pd.DataFrame()
        
        return self.contingency_results.nlargest(top_n, 'load_percentage')

    def get_contingencies_by_outage(self, component_name: str) -> pd.DataFrame:
        """
        Get all impacts for a specific outaged component.
        
        Args:
            component_name: Name of the outaged component to filter by
        
        Returns:
            DataFrame of all affected branches for the given outage
        """
        if self.contingency_results is None or len(self.contingency_results) == 0:
            print("No contingency results available. Run run_n1_analysis() first.")
            return pd.DataFrame()
        
        return self.contingency_results[
            self.contingency_results['outaged_component'] == component_name
        ]

    def export_summary(self, filepath: str = "n1_contingency_summary.csv"):
        """
        Export contingency analysis results to CSV.
        
        Args:
            filepath: Path to save the CSV file
        """
        if self.contingency_results is None or len(self.contingency_results) == 0:
            print("No contingency results available. Run run_n1_analysis() first.")
            return
        
        self.contingency_results.to_csv(filepath, index=False)
        print(f"N-1 contingency results exported to {filepath}")
