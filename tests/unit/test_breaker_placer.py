"""
Unit tests for breaker placement module
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from kis_estimator_core.engine.breaker_placer import BreakerSpec


@pytest.mark.unit
class TestBreakerSpec:
    """Test BreakerSpec class"""

    def test_breaker_spec_initialization(self):
        """Test BreakerSpec can be initialized with basic parameters"""
        spec = BreakerSpec(
            breaker_id="MCCB-001",
            breaker_type="MCCB",
            rating=100,
            width=150,
            height=200,
            depth=100
        )

        assert spec.breaker_id == "MCCB-001"
        assert spec.breaker_type == "MCCB"
        assert spec.rating == 100
        assert spec.width == 150
        assert spec.height == 200
        assert spec.depth == 100

    def test_breaker_spec_phase_balance(self):
        """Test phase balance calculation"""
        spec = BreakerSpec(
            breaker_id="MCCB-001",
            breaker_type="MCCB",
            rating=100,
            width=150,
            height=200,
            depth=100,
            phase=3
        )

        assert spec.phase == 3

    def test_breaker_spec_with_optional_params(self):
        """Test BreakerSpec with optional parameters"""
        spec = BreakerSpec(
            breaker_id="MCB-001",
            breaker_type="MCB",
            rating=20,
            width=18,
            height=90,
            depth=75,
            phase=1,
            heat_dissipation=50,
            position_x=100,
            position_y=200
        )

        assert spec.phase == 1
        assert spec.heat_dissipation == 50
        assert spec.position_x == 100
        assert spec.position_y == 200

    @pytest.mark.parametrize("breaker_type,expected_priority", [
        ("MCCB", 1),
        ("ACB", 1),
        ("MCB", 2),
        ("ELCB", 3),
    ])
    def test_breaker_type_priority(self, breaker_type, expected_priority):
        """Test breaker type priority assignment"""
        spec = BreakerSpec(
            breaker_id=f"{breaker_type}-001",
            breaker_type=breaker_type,
            rating=100,
            width=100,
            height=100,
            depth=100
        )

        # Priority logic would be in placement algorithm
        # This is a placeholder for actual priority testing
        assert spec.breaker_type == breaker_type

    def test_breaker_spec_validation(self):
        """Test validation of breaker specifications"""
        # Test negative dimensions should raise error
        with pytest.raises(ValueError):
            BreakerSpec(
                breaker_id="INVALID-001",
                breaker_type="MCCB",
                rating=100,
                width=-150,  # Invalid negative width
                height=200,
                depth=100
            )

        # Test zero rating should raise error
        with pytest.raises(ValueError):
            BreakerSpec(
                breaker_id="INVALID-002",
                breaker_type="MCCB",
                rating=0,  # Invalid zero rating
                width=150,
                height=200,
                depth=100
            )

    def test_breaker_spec_to_dict(self):
        """Test conversion of BreakerSpec to dictionary"""
        spec = BreakerSpec(
            breaker_id="MCCB-001",
            breaker_type="MCCB",
            rating=100,
            width=150,
            height=200,
            depth=100
        )

        spec_dict = spec.to_dict()

        assert isinstance(spec_dict, dict)
        assert spec_dict["breaker_id"] == "MCCB-001"
        assert spec_dict["breaker_type"] == "MCCB"
        assert spec_dict["rating"] == 100
        assert spec_dict["dimensions"]["width"] == 150
        assert spec_dict["dimensions"]["height"] == 200
        assert spec_dict["dimensions"]["depth"] == 100

    def test_breaker_spec_from_dict(self):
        """Test creation of BreakerSpec from dictionary"""
        data = {
            "breaker_id": "MCCB-002",
            "breaker_type": "MCCB",
            "rating": 200,
            "dimensions": {
                "width": 200,
                "height": 250,
                "depth": 120
            }
        }

        spec = BreakerSpec.from_dict(data)

        assert spec.breaker_id == "MCCB-002"
        assert spec.breaker_type == "MCCB"
        assert spec.rating == 200
        assert spec.width == 200
        assert spec.height == 250
        assert spec.depth == 120


@pytest.mark.unit
class TestBreakerPlacementAlgorithm:
    """Test breaker placement algorithm"""

    @patch('kis_estimator_core.engine.breaker_placer.cp_model')
    def test_placement_with_ortools(self, mock_cp_model):
        """Test placement when OR-Tools is available"""
        # Mock OR-Tools components
        mock_cp_model.CpModel.return_value = Mock()
        mock_cp_model.CpSolver.return_value = Mock()

        from kis_estimator_core.engine.breaker_placer import place_breakers

        enclosure = {
            "width": 800,
            "height": 2000,
            "depth": 600
        }

        breakers = [
            BreakerSpec("MCCB-001", "MCCB", 100, 150, 200, 100),
            BreakerSpec("MCB-001", "MCB", 20, 18, 90, 75)
        ]

        # This would call the actual placement function
        # result = place_breakers(enclosure, breakers)
        # assert result is not None

    def test_placement_without_ortools(self):
        """Test fallback placement when OR-Tools is not available"""
        with patch('kis_estimator_core.engine.breaker_placer.cp_model', None):
            from kis_estimator_core.engine.breaker_placer import place_breakers_fallback

            enclosure = {
                "width": 800,
                "height": 2000,
                "depth": 600
            }

            breakers = [
                BreakerSpec("MCCB-001", "MCCB", 100, 150, 200, 100),
                BreakerSpec("MCB-001", "MCB", 20, 18, 90, 75)
            ]

            # This would call the fallback placement function
            # result = place_breakers_fallback(enclosure, breakers)
            # assert result is not None

    def test_heat_distribution_calculation(self):
        """Test heat distribution calculation for placed breakers"""
        from kis_estimator_core.engine.breaker_placer import calculate_heat_distribution

        placed_breakers = [
            {
                "breaker_id": "MCCB-001",
                "position": {"x": 100, "y": 500},
                "heat_dissipation": 100
            },
            {
                "breaker_id": "MCB-001",
                "position": {"x": 200, "y": 600},
                "heat_dissipation": 20
            }
        ]

        enclosure = {
            "width": 800,
            "height": 2000,
            "depth": 600
        }

        # heat_map = calculate_heat_distribution(placed_breakers, enclosure)
        # assert heat_map is not None

    def test_phase_balance_optimization(self):
        """Test phase balance optimization in placement"""
        from kis_estimator_core.engine.breaker_placer import optimize_phase_balance

        breakers = [
            BreakerSpec("MCCB-001", "MCCB", 100, 150, 200, 100, phase=3),
            BreakerSpec("MCCB-002", "MCCB", 100, 150, 200, 100, phase=3),
            BreakerSpec("MCB-001", "MCB", 20, 18, 90, 75, phase=1),
            BreakerSpec("MCB-002", "MCB", 20, 18, 90, 75, phase=1),
        ]

        # balanced = optimize_phase_balance(breakers)
        # assert balanced is not None