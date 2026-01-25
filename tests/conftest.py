"""Shared pytest fixtures."""

from pathlib import Path
from unittest.mock import Mock

import pytest


# === Path Fixtures ===


@pytest.fixture
def fixtures_path() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def config_fixtures_path(fixtures_path: Path) -> Path:
    """Path to config fixtures."""
    return fixtures_path / "config"


@pytest.fixture
def test_plan_fixtures_path(fixtures_path: Path) -> Path:
    """Path to test plan fixtures."""
    return fixtures_path / "test_plans"


# === Mock Fixtures ===


@pytest.fixture
def mock_visa_resource() -> Mock:
    """Mock PyVISA resource."""
    resource = Mock()
    resource.query.return_value = "Manufacturer,Model,Serial,1.0.0"
    resource.read.return_value = "response"
    resource.timeout = 5000
    return resource


@pytest.fixture
def mock_visa_connection() -> Mock:
    """Mock VISAConnection."""
    conn = Mock()
    conn.is_open = False

    def open_side_effect() -> None:
        conn.is_open = True

    def close_side_effect() -> None:
        conn.is_open = False

    conn.open.side_effect = open_side_effect
    conn.close.side_effect = close_side_effect
    conn.list_resources.return_value = ("TCPIP::192.168.1.100::INSTR",)

    # Return a mock resource when open_resource is called
    mock_resource = Mock()
    mock_resource.query.return_value = "MockMfg,MockModel,12345,1.0"
    mock_resource.timeout = 5000
    conn.open_resource.return_value = mock_resource

    return conn


@pytest.fixture
def mock_power_supply() -> Mock:
    """Mock PowerSupply instrument."""
    ps = Mock()
    ps.is_connected = False
    ps.identification = "MockMfg,MockPS,12345,1.0"
    ps.resource_address = "TCPIP::192.168.1.100::INSTR"
    ps._timeout_ms = 5000
    ps._read_termination = "\n"
    ps._write_termination = "\n"

    def connect_side_effect(resource: Mock) -> None:
        ps.is_connected = True

    def disconnect_side_effect() -> None:
        ps.is_connected = False

    ps.connect.side_effect = connect_side_effect
    ps.disconnect.side_effect = disconnect_side_effect

    return ps


@pytest.fixture
def mock_signal_generator() -> Mock:
    """Mock SignalGenerator instrument."""
    sg = Mock()
    sg.is_connected = False
    sg.identification = "MockMfg,MockSG,67890,2.0"
    sg.resource_address = "TCPIP::192.168.1.101::INSTR"
    sg._timeout_ms = 5000
    sg._read_termination = "\n"
    sg._write_termination = "\n"

    def connect_side_effect(resource: Mock) -> None:
        sg.is_connected = True

    def disconnect_side_effect() -> None:
        sg.is_connected = False

    sg.connect.side_effect = connect_side_effect
    sg.disconnect.side_effect = disconnect_side_effect

    return sg


# === Model Fixtures ===


@pytest.fixture
def state_machine():
    """Fresh StateMachine instance."""
    from visa_vulture.model.state_machine import StateMachine

    return StateMachine()


@pytest.fixture
def equipment_model(mock_visa_connection: Mock):
    """EquipmentModel with mock VISA connection."""
    from visa_vulture.model.equipment import EquipmentModel

    return EquipmentModel(mock_visa_connection)


# === Test Plan Fixtures ===


@pytest.fixture
def sample_power_supply_plan():
    """Sample PowerSupply test plan."""
    from visa_vulture.model.test_plan import (
        PLAN_TYPE_POWER_SUPPLY,
        PowerSupplyTestStep,
        TestPlan,
    )

    return TestPlan(
        name="Test Plan",
        plan_type=PLAN_TYPE_POWER_SUPPLY,
        steps=[
            PowerSupplyTestStep(
                step_number=1, time_seconds=0.0, voltage=5.0, current=1.0
            ),
            PowerSupplyTestStep(
                step_number=2, time_seconds=1.0, voltage=10.0, current=2.0
            ),
        ],
    )


@pytest.fixture
def sample_signal_generator_plan():
    """Sample SignalGenerator test plan."""
    from visa_vulture.model.test_plan import (
        PLAN_TYPE_SIGNAL_GENERATOR,
        SignalGeneratorTestStep,
        TestPlan,
    )

    return TestPlan(
        name="SG Test Plan",
        plan_type=PLAN_TYPE_SIGNAL_GENERATOR,
        steps=[
            SignalGeneratorTestStep(
                step_number=1, time_seconds=0.0, frequency=1e6, power=0
            ),
            SignalGeneratorTestStep(
                step_number=2, time_seconds=1.0, frequency=2e6, power=-10
            ),
        ],
    )


# === Integration Test Fixtures ===


@pytest.fixture
def simulation_yaml_path() -> Path:
    """Path to simulation YAML file."""
    return Path(__file__).parent.parent / "visa_vulture" / "simulation" / "instruments.yaml"


@pytest.fixture
def visa_connection_sim(simulation_yaml_path: Path):
    """Real VISAConnection with simulation backend."""
    from visa_vulture.instruments import VISAConnection

    conn = VISAConnection(simulation_mode=True, simulation_file=simulation_yaml_path)
    yield conn
    if conn.is_open:
        conn.close()
