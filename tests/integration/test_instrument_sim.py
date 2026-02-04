"""Integration tests using PyVISA-sim backend."""

from pathlib import Path

import pytest

from visa_vulture.instruments import PowerSupply, SignalGenerator, VISAConnection


@pytest.mark.integration
class TestVISAConnectionSim:
    """Tests for VISAConnection with simulation backend."""

    def test_open_with_simulation_backend(
        self, visa_connection_sim: VISAConnection
    ) -> None:
        """VISAConnection can open with simulation backend."""
        visa_connection_sim.open()
        assert visa_connection_sim.is_open is True

    def test_list_resources_finds_simulated_instruments(
        self, visa_connection_sim: VISAConnection
    ) -> None:
        """list_resources returns simulated instruments."""
        visa_connection_sim.open()
        resources = visa_connection_sim.list_resources()

        assert len(resources) >= 2
        # Check for expected simulated resources
        resource_list = list(resources)
        assert any("192.168.1.100" in r for r in resource_list)
        assert any("192.168.1.101" in r for r in resource_list)

    def test_open_resource(self, visa_connection_sim: VISAConnection) -> None:
        """open_resource returns a valid resource."""
        visa_connection_sim.open()
        resource = visa_connection_sim.open_resource("TCPIP::192.168.1.100::INSTR")

        assert resource is not None

    def test_context_manager(self, simulation_yaml_path: Path) -> None:
        """VISAConnection works as context manager."""
        with VISAConnection(
            simulation_mode=True, simulation_file=simulation_yaml_path
        ) as conn:
            conn.open()
            assert conn.is_open is True
        # After context exits, connection should be closed
        assert conn.is_open is False


@pytest.mark.integration
class TestPowerSupplySim:
    """Tests for PowerSupply with simulated instrument."""

    @pytest.fixture
    def connected_power_supply(
        self, visa_connection_sim: VISAConnection
    ) -> PowerSupply:
        """Fixture providing a connected power supply."""
        visa_connection_sim.open()
        resource = visa_connection_sim.open_resource("TCPIP::192.168.1.100::INSTR")

        ps = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        ps.connect(resource)
        return ps

    def test_connect_and_identify(self, connected_power_supply: PowerSupply) -> None:
        """Power supply connects and returns identification."""
        assert connected_power_supply.is_connected is True
        assert connected_power_supply.identification is not None
        assert "SimPower" in connected_power_supply.identification
        assert connected_power_supply.manufacturer() == "SimPower"
        assert connected_power_supply.model() == "PS-1000"

    def test_set_and_get_voltage(self, connected_power_supply: PowerSupply) -> None:
        """Voltage can be set and read back."""
        connected_power_supply.set_voltage(5.0)
        voltage = connected_power_supply.get_voltage()

        assert voltage == pytest.approx(5.0, abs=0.001)

    def test_set_and_get_current(self, connected_power_supply: PowerSupply) -> None:
        """Current can be set and read back."""
        connected_power_supply.set_current(1.5)
        current = connected_power_supply.get_current()

        assert current == pytest.approx(1.5, abs=0.001)

    def test_enable_disable_output(self, connected_power_supply: PowerSupply) -> None:
        """Output can be enabled and disabled."""
        connected_power_supply.enable_output()
        assert connected_power_supply.is_output_enabled() is True

        connected_power_supply.disable_output()
        assert connected_power_supply.is_output_enabled() is False

    def test_get_status(self, connected_power_supply: PowerSupply) -> None:
        """get_status returns dictionary with status values."""
        connected_power_supply.set_voltage(10.0)
        connected_power_supply.set_current(2.0)

        status = connected_power_supply.get_status()

        assert "voltage" in status
        assert "current" in status
        assert "output_enabled" in status
        assert status["voltage"] == pytest.approx(10.0, abs=0.001)
        assert status["current"] == pytest.approx(2.0, abs=0.001)

    def test_reset(self, connected_power_supply: PowerSupply) -> None:
        """reset command is accepted."""
        # Just verify it doesn't raise
        connected_power_supply.reset()

    def test_operation_complete(self, connected_power_supply: PowerSupply) -> None:
        """operation_complete returns True for simulation."""
        result = connected_power_supply.operation_complete()
        assert result is True


@pytest.mark.integration
class TestSignalGeneratorSim:
    """Tests for SignalGenerator with simulated instrument."""

    @pytest.fixture
    def connected_signal_generator(
        self, visa_connection_sim: VISAConnection
    ) -> SignalGenerator:
        """Fixture providing a connected signal generator."""
        visa_connection_sim.open()
        resource = visa_connection_sim.open_resource("TCPIP::192.168.1.101::INSTR")

        sg = SignalGenerator(
            name="Test SG",
            resource_address="TCPIP::192.168.1.101::INSTR",
        )
        sg.connect(resource)
        return sg

    def test_connect_and_identify(
        self, connected_signal_generator: SignalGenerator
    ) -> None:
        """Signal generator connects and returns identification."""
        assert connected_signal_generator.is_connected is True
        assert connected_signal_generator.identification is not None
        assert "SimGen" in connected_signal_generator.identification
        assert connected_signal_generator.manufacturer() == "SimGen"
        assert connected_signal_generator.model() == "SG-2000"

    def test_set_and_get_frequency(
        self, connected_signal_generator: SignalGenerator
    ) -> None:
        """Frequency can be set and read back."""
        connected_signal_generator.set_frequency(2e6)  # 2 MHz
        frequency = connected_signal_generator.get_frequency()

        assert frequency == pytest.approx(2e6, abs=100)

    def test_set_and_get_power(
        self, connected_signal_generator: SignalGenerator
    ) -> None:
        """Power can be set and read back."""
        connected_signal_generator.set_power(-5.0)  # -5 dBm
        power = connected_signal_generator.get_power()

        assert power == pytest.approx(-5.0, abs=0.01)

    def test_enable_disable_output(
        self, connected_signal_generator: SignalGenerator
    ) -> None:
        """Output can be enabled and disabled."""
        connected_signal_generator.enable_output()
        assert connected_signal_generator.is_output_enabled() is True

        connected_signal_generator.disable_output()
        assert connected_signal_generator.is_output_enabled() is False

    def test_get_status(self, connected_signal_generator: SignalGenerator) -> None:
        """get_status returns dictionary with status values."""
        connected_signal_generator.set_frequency(1.5e6)
        connected_signal_generator.set_power(-10.0)

        status = connected_signal_generator.get_status()

        assert "frequency" in status
        assert "power" in status
        assert "output_enabled" in status
        assert status["frequency"] == pytest.approx(1.5e6, abs=100)
        assert status["power"] == pytest.approx(-10.0, abs=0.01)

    def test_reset(self, connected_signal_generator: SignalGenerator) -> None:
        """reset command is accepted."""
        # Just verify it doesn't raise
        connected_signal_generator.reset()

    def test_operation_complete(
        self, connected_signal_generator: SignalGenerator
    ) -> None:
        """operation_complete returns True for simulation."""
        result = connected_signal_generator.operation_complete()
        assert result is True
