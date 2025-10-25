from pytest import fixture
from source.network import Network
import pytest

@fixture
def network():
    return Network()

def test_network_creation(network):
    assert network is not None

def test_network_solve(network):
    network.solve()
    assert network.subnet is not None


class TestNetworkConductorRatings:
    """Test Network.apply_atmospherics() calculates correct conductor thermal ratings"""
    
    # Ambient parameters matching calculate_nominal_ratings.py
    AMBIENT_DEFAULTS = {
        'Ta': 25,
        'WindVelocity': 2.0, 
        'WindAngleDeg': 90,
        'SunTime': 12,
        'Elevation': 1000,
        'Latitude': 27,
        'Emissivity': 0.8,
        'Absorptivity': 0.8,
        'Direction': 'EastWest',
        'Atmosphere': 'Clear',
        'Date': '12 Jun',
    }
    
    # Expected ratings at 75°C for specific conductors (from conductor_ratings.csv)
    EXPECTED_RATINGS = {
        '336.4 ACSR 30/7 ORIOLE': {
            'MOT': 75,
            'RatingAmps': 531,
            'RatingMVA_69': 63,
            'RatingMVA_138': 127,
        },
        '795 ACSR 26/7 DRAKE': {
            'MOT': 75,
            'RatingAmps': 902,
            'RatingMVA_69': 107,
            'RatingMVA_138': 215,
        },
        '1590 ACSR 54/19 FALCON': {
            'MOT': 75,
            'RatingAmps': 1349,
            'RatingMVA_69': 161,
            'RatingMVA_138': 322,
        },
    }
    
    def test_apply_atmospherics_oriole_75c(self, network):
        """Test ORIOLE conductor at 75°C matches expected rating"""
        network.apply_atmospherics(**self.AMBIENT_DEFAULTS)
        
        # Find lines with ORIOLE conductor at 75C
        oriole_lines = network.subnet.lines[
            (network.subnet.lines['conductor'] == '336.4 ACSR 30/7 ORIOLE') &
            (network.subnet.lines['MOT'] == 75)
        ]
        
        assert len(oriole_lines) > 0, "No ORIOLE lines at 75°C found in network"
        
        expected_mva = self.EXPECTED_RATINGS['336.4 ACSR 30/7 ORIOLE']['RatingMVA_69']
        for _, line in oriole_lines.iterrows():
            assert line['s_nom'] == pytest.approx(expected_mva, abs=1), (
                f"ORIOLE at 75°C: Expected {expected_mva} MVA, got {line['s_nom']} MVA"
            )
    
    def test_network_lines_have_heat_balance_terms(self, network):
        """Test that apply_atmospherics adds heat balance calculation terms (Qs, Qc, Qr)"""
        network.apply_atmospherics(**self.AMBIENT_DEFAULTS)
        
        # Verify that heat balance terms are added to lines
        assert 'Qs' in network.subnet.lines.columns, "Qs (solar heating) not found in lines"
        assert 'Qc' in network.subnet.lines.columns, "Qc (convective cooling) not found in lines"
        assert 'Qr' in network.subnet.lines.columns, "Qr (radiative cooling) not found in lines"
        
        # Verify all lines have calculated values
        for col in ['Qs', 'Qc', 'Qr']:
            assert network.subnet.lines[col].notna().all(), (
                f"Column {col} contains NaN values"
            )
    
    def test_network_reset_clears_ratings(self, network):
        """Test that reset() clears calculated ratings"""
        # Apply atmospherics first
        network.apply_atmospherics(**self.AMBIENT_DEFAULTS)
        assert 'Qs' in network.subnet.lines.columns
        
        # Reset network
        network.reset()
        
        # Verify heat balance columns are removed
        assert 'Qs' not in network.subnet.lines.columns, "Reset did not clear Qs column"
        assert 'Qc' not in network.subnet.lines.columns, "Reset did not clear Qc column"
        assert 'Qr' not in network.subnet.lines.columns, "Reset did not clear Qr column"
    
    def test_apply_atmospherics_modifies_s_nom(self, network):
        """Test that apply_atmospherics modifies the s_nom (apparent power rating) for lines"""
        original_s_nom = network.subnet.lines['s_nom'].copy()
        
        network.apply_atmospherics(**self.AMBIENT_DEFAULTS)
        
        new_s_nom = network.subnet.lines['s_nom']
        
        # Verify that s_nom values were updated
        assert not original_s_nom.equals(new_s_nom), (
            "s_nom values were not modified by apply_atmospherics"
        )
        
        # Verify all s_nom values are positive
        assert (new_s_nom > 0).all(), "Some s_nom values are not positive"

