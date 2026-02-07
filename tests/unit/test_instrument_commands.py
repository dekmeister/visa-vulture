"""Tests for instrument-specific commands (signal generator and power supply).

These tests verify that each instrument method sends the correct SCPI command
strings and correctly parses responses. Uses mock VISA resources to avoid
hardware dependency.
"""

from unittest.mock import Mock, call

import pytest

from visa_vulture.instruments.power_supply import PowerSupply
from visa_vulture.instruments.signal_generator import SignalGenerator


def _make_connected_power_supply(mock_resource: Mock) -> PowerSupply:
    """Create a connected power supply with a mock resource."""
    ps = PowerSupply(name="Test PS", resource_address="TCPIP::1.2.3.4::INSTR")
    ps.connect(mock_resource)
    return ps


def _make_connected_signal_generator(mock_resource: Mock) -> SignalGenerator:
    """Create a connected signal generator with a mock resource."""
    sg = SignalGenerator(name="Test SG", resource_address="TCPIP::1.2.3.4::INSTR")
    sg.connect(mock_resource)
    return sg


class TestPowerSupplyMeasurements:
    """Tests for power supply measurement and query methods."""

    def test_measure_voltage_sends_correct_query(
        self, mock_visa_resource: Mock
    ) -> None:
        """measure_voltage sends MEAS:VOLT? and returns parsed float."""
        mock_visa_resource.query.return_value = "5.123456\n"
        ps = _make_connected_power_supply(mock_visa_resource)

        result = ps.measure_voltage()

        mock_visa_resource.query.assert_called_with("MEAS:VOLT?")
        assert result == pytest.approx(5.123456)

    def test_measure_current_sends_correct_query(
        self, mock_visa_resource: Mock
    ) -> None:
        """measure_current sends MEAS:CURR? and returns parsed float."""
        mock_visa_resource.query.return_value = "1.500000\n"
        ps = _make_connected_power_supply(mock_visa_resource)

        result = ps.measure_current()

        mock_visa_resource.query.assert_called_with("MEAS:CURR?")
        assert result == pytest.approx(1.5)

    def test_measure_power_returns_voltage_times_current(
        self, mock_visa_resource: Mock
    ) -> None:
        """measure_power returns measured voltage * measured current."""
        mock_visa_resource.query.side_effect = lambda cmd: {
            "MEAS:VOLT?": "5.0\n",
            "MEAS:CURR?": "2.0\n",
        }[cmd]
        ps = _make_connected_power_supply(mock_visa_resource)

        result = ps.measure_power()

        assert result == pytest.approx(10.0)

    def test_get_status_returns_complete_dict(
        self, mock_visa_resource: Mock
    ) -> None:
        """get_status returns dict with voltage, current, and output state."""
        mock_visa_resource.query.side_effect = lambda cmd: {
            "VOLT?": "12.0\n",
            "CURR?": "3.0\n",
            "OUTP?": "1\n",
        }[cmd]
        ps = _make_connected_power_supply(mock_visa_resource)

        status = ps.get_status()

        assert status["voltage"] == pytest.approx(12.0)
        assert status["current"] == pytest.approx(3.0)
        assert status["output_enabled"] is True


class TestSignalGeneratorAMModulation:
    """Tests for AM modulation SCPI commands."""

    def test_configure_am_modulation_sends_correct_commands(
        self, mock_visa_resource: Mock
    ) -> None:
        """configure_am_modulation sends source, frequency, and depth commands."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.configure_am_modulation(modulation_frequency=1000.0, depth=50.0)

        write_calls = mock_visa_resource.write.call_args_list
        # Filter to only AM-related writes (skip *IDN? etc from connect)
        am_calls = [c for c in write_calls if "AM:" in str(c)]
        assert call("AM:SOUR INT") in am_calls
        assert call("AM:INT:FREQ 1000.0") in am_calls
        assert call("AM:DEPT 50.0") in am_calls

    def test_enable_am_modulation_sends_command(
        self, mock_visa_resource: Mock
    ) -> None:
        """enable_am_modulation sends AM:STAT 1."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.enable_am_modulation()

        mock_visa_resource.write.assert_called_with("AM:STAT 1")

    def test_disable_am_modulation_sends_command(
        self, mock_visa_resource: Mock
    ) -> None:
        """disable_am_modulation sends AM:STAT 0."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.disable_am_modulation()

        mock_visa_resource.write.assert_called_with("AM:STAT 0")

    def test_is_am_enabled_returns_true_for_1(
        self, mock_visa_resource: Mock
    ) -> None:
        """is_am_enabled returns True when response is '1'."""
        mock_visa_resource.query.return_value = "1\n"
        sg = _make_connected_signal_generator(mock_visa_resource)

        assert sg.is_am_enabled() is True

    def test_is_am_enabled_returns_true_for_on(
        self, mock_visa_resource: Mock
    ) -> None:
        """is_am_enabled returns True when response is 'ON'."""
        mock_visa_resource.query.return_value = "ON\n"
        sg = _make_connected_signal_generator(mock_visa_resource)

        assert sg.is_am_enabled() is True

    def test_is_am_enabled_returns_false_for_0(
        self, mock_visa_resource: Mock
    ) -> None:
        """is_am_enabled returns False when response is '0'."""
        mock_visa_resource.query.return_value = "0\n"
        sg = _make_connected_signal_generator(mock_visa_resource)

        assert sg.is_am_enabled() is False


class TestSignalGeneratorFMModulation:
    """Tests for FM modulation SCPI commands."""

    def test_configure_fm_modulation_sends_correct_commands(
        self, mock_visa_resource: Mock
    ) -> None:
        """configure_fm_modulation sends source, frequency, and deviation commands."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.configure_fm_modulation(modulation_frequency=500.0, deviation=10000.0)

        write_calls = mock_visa_resource.write.call_args_list
        fm_calls = [c for c in write_calls if "FM:" in str(c)]
        assert call("FM:SOUR INT") in fm_calls
        assert call("FM:INT:FREQ 500.0") in fm_calls
        assert call("FM:DEV 10000.0") in fm_calls

    def test_enable_fm_modulation_sends_command(
        self, mock_visa_resource: Mock
    ) -> None:
        """enable_fm_modulation sends FM:STAT 1."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.enable_fm_modulation()

        mock_visa_resource.write.assert_called_with("FM:STAT 1")

    def test_disable_fm_modulation_sends_command(
        self, mock_visa_resource: Mock
    ) -> None:
        """disable_fm_modulation sends FM:STAT 0."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.disable_fm_modulation()

        mock_visa_resource.write.assert_called_with("FM:STAT 0")

    def test_is_fm_enabled_returns_true_for_1(
        self, mock_visa_resource: Mock
    ) -> None:
        """is_fm_enabled returns True when response is '1'."""
        mock_visa_resource.query.return_value = "1\n"
        sg = _make_connected_signal_generator(mock_visa_resource)

        assert sg.is_fm_enabled() is True

    def test_is_fm_enabled_returns_false_for_0(
        self, mock_visa_resource: Mock
    ) -> None:
        """is_fm_enabled returns False when response is '0'."""
        mock_visa_resource.query.return_value = "0\n"
        sg = _make_connected_signal_generator(mock_visa_resource)

        assert sg.is_fm_enabled() is False


class TestSignalGeneratorModulationDispatch:
    """Tests for generic modulation dispatch methods."""

    def test_configure_modulation_dispatches_am(
        self, mock_visa_resource: Mock
    ) -> None:
        """configure_modulation calls configure_am_modulation for AM config."""
        from visa_vulture.model.test_plan import AMModulationConfig, ModulationType

        sg = _make_connected_signal_generator(mock_visa_resource)
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=50.0,
        )

        sg.configure_modulation(config)

        write_calls = [str(c) for c in mock_visa_resource.write.call_args_list]
        assert any("AM:SOUR INT" in c for c in write_calls)
        assert any("AM:DEPT 50.0" in c for c in write_calls)

    def test_configure_modulation_dispatches_fm(
        self, mock_visa_resource: Mock
    ) -> None:
        """configure_modulation calls configure_fm_modulation for FM config."""
        from visa_vulture.model.test_plan import FMModulationConfig, ModulationType

        sg = _make_connected_signal_generator(mock_visa_resource)
        config = FMModulationConfig(
            modulation_type=ModulationType.FM,
            modulation_frequency=500.0,
            deviation=10000.0,
        )

        sg.configure_modulation(config)

        write_calls = [str(c) for c in mock_visa_resource.write.call_args_list]
        assert any("FM:SOUR INT" in c for c in write_calls)
        assert any("FM:DEV 10000.0" in c for c in write_calls)

    def test_set_modulation_enabled_am_enable(
        self, mock_visa_resource: Mock
    ) -> None:
        """set_modulation_enabled enables AM modulation."""
        from visa_vulture.model.test_plan import AMModulationConfig, ModulationType

        sg = _make_connected_signal_generator(mock_visa_resource)
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=50.0,
        )

        sg.set_modulation_enabled(config, True)

        mock_visa_resource.write.assert_called_with("AM:STAT 1")

    def test_set_modulation_enabled_am_disable(
        self, mock_visa_resource: Mock
    ) -> None:
        """set_modulation_enabled disables AM modulation."""
        from visa_vulture.model.test_plan import AMModulationConfig, ModulationType

        sg = _make_connected_signal_generator(mock_visa_resource)
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=50.0,
        )

        sg.set_modulation_enabled(config, False)

        mock_visa_resource.write.assert_called_with("AM:STAT 0")

    def test_set_modulation_enabled_fm_enable(
        self, mock_visa_resource: Mock
    ) -> None:
        """set_modulation_enabled enables FM modulation."""
        from visa_vulture.model.test_plan import FMModulationConfig, ModulationType

        sg = _make_connected_signal_generator(mock_visa_resource)
        config = FMModulationConfig(
            modulation_type=ModulationType.FM,
            modulation_frequency=500.0,
            deviation=10000.0,
        )

        sg.set_modulation_enabled(config, True)

        mock_visa_resource.write.assert_called_with("FM:STAT 1")

    def test_set_modulation_enabled_fm_disable(
        self, mock_visa_resource: Mock
    ) -> None:
        """set_modulation_enabled disables FM modulation."""
        from visa_vulture.model.test_plan import FMModulationConfig, ModulationType

        sg = _make_connected_signal_generator(mock_visa_resource)
        config = FMModulationConfig(
            modulation_type=ModulationType.FM,
            modulation_frequency=500.0,
            deviation=10000.0,
        )

        sg.set_modulation_enabled(config, False)

        mock_visa_resource.write.assert_called_with("FM:STAT 0")

    def test_disable_all_modulation_disables_both(
        self, mock_visa_resource: Mock
    ) -> None:
        """disable_all_modulation sends AM:STAT 0 and FM:STAT 0."""
        sg = _make_connected_signal_generator(mock_visa_resource)

        sg.disable_all_modulation()

        write_calls = mock_visa_resource.write.call_args_list
        assert call("AM:STAT 0") in write_calls
        assert call("FM:STAT 0") in write_calls


class TestSignalGeneratorGetStatus:
    """Tests for signal generator get_status method."""

    def test_get_status_returns_complete_dict(
        self, mock_visa_resource: Mock
    ) -> None:
        """get_status returns dict with frequency, power, output, and modulation state."""
        mock_visa_resource.query.side_effect = lambda cmd: {
            "FREQ?": "1000000.0\n",
            "POW?": "-10.00\n",
            "OUTP?": "0\n",
            "AM:STAT?": "0\n",
            "FM:STAT?": "0\n",
        }[cmd]
        sg = _make_connected_signal_generator(mock_visa_resource)

        status = sg.get_status()

        assert status["frequency"] == pytest.approx(1e6)
        assert status["power"] == pytest.approx(-10.0)
        assert status["output_enabled"] is False
        assert status["am_enabled"] is False
        assert status["fm_enabled"] is False
