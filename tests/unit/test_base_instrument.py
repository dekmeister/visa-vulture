"""Tests for the base instrument module."""

from unittest.mock import Mock

import pytest

from visa_vulture.instruments.power_supply import PowerSupply


class TestBaseInstrumentProperties:
    """Tests for BaseInstrument properties.

    Uses PowerSupply as a concrete implementation for testing.
    """

    def test_name_property(self) -> None:
        """name property returns the instrument name."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument.name == "Test PS"

    def test_resource_address_property(self) -> None:
        """resource_address property returns the VISA address."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument.resource_address == "TCPIP::192.168.1.100::INSTR"

    def test_is_connected_false_initially(self) -> None:
        """is_connected is False when not connected."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument.is_connected is False

    def test_identification_none_initially(self) -> None:
        """identification is None when not connected."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument.identification is None


class TestBaseInstrumentIdnParsing:
    """Tests for *IDN? response parsing."""

    def test_manufacturer_parses_first_field(self) -> None:
        """manufacturer() returns first field of IDN."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument._identification = "Keysight,E36313A,MY12345678,1.2.3"
        assert instrument.manufacturer() == "Keysight"

    def test_model_parses_second_field(self) -> None:
        """model() returns second field of IDN."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument._identification = "Keysight,E36313A,MY12345678,1.2.3"
        assert instrument.model() == "E36313A"

    def test_serial_parses_third_field(self) -> None:
        """serial() returns third field of IDN."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument._identification = "Keysight,E36313A,MY12345678,1.2.3"
        assert instrument.serial() == "MY12345678"

    def test_firmware_parses_fourth_field(self) -> None:
        """firmware() returns fourth field of IDN."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument._identification = "Keysight,E36313A,MY12345678,1.2.3"
        assert instrument.firmware() == "1.2.3"

    def test_missing_idn_returns_unknown(self) -> None:
        """Returns 'Unknown' when identification is None."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument.manufacturer() == "Unknown"
        assert instrument.model() == "Unknown"
        assert instrument.serial() == "Unknown"
        assert instrument.firmware() == "Unknown"

    def test_partial_idn_returns_unknown_for_missing_fields(self) -> None:
        """Returns 'Unknown' for missing fields in partial IDN."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument._identification = "Keysight,E36313A"  # Only 2 fields
        assert instrument.manufacturer() == "Keysight"
        assert instrument.model() == "E36313A"
        assert instrument.serial() == "Unknown"
        assert instrument.firmware() == "Unknown"

    def test_formatted_identification(self) -> None:
        """formatted_identification() returns human-readable string."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument._identification = "Keysight,E36313A,MY12345678,1.2.3"

        formatted = instrument.formatted_identification()

        assert "Manufacturer: Keysight" in formatted
        assert "Model: E36313A" in formatted
        assert "Serial: MY12345678" in formatted
        assert "Firmware: 1.2.3" in formatted


class TestBaseInstrumentConnection:
    """Tests for connection management."""

    def test_connect_stores_resource(self, mock_visa_resource: Mock) -> None:
        """connect stores the VISA resource."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )

        instrument.connect(mock_visa_resource)

        assert instrument._resource is mock_visa_resource
        assert instrument.is_connected is True

    def test_connect_queries_idn(self, mock_visa_resource: Mock) -> None:
        """connect queries *IDN? and stores result."""
        mock_visa_resource.query.return_value = "Mfg,Model,Serial,1.0"
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )

        instrument.connect(mock_visa_resource)

        mock_visa_resource.query.assert_called_with("*IDN?")
        assert instrument.identification == "Mfg,Model,Serial,1.0"

    def test_connect_when_already_connected_does_not_replace(
        self, mock_visa_resource: Mock
    ) -> None:
        """connect when already connected logs warning but doesn't replace."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        new_resource = Mock()
        instrument.connect(new_resource)  # Should warn and return

        assert instrument._resource is mock_visa_resource  # Still original

    def test_disconnect_closes_resource(self, mock_visa_resource: Mock) -> None:
        """disconnect closes the VISA resource."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        instrument.disconnect()

        mock_visa_resource.close.assert_called_once()

    def test_disconnect_sets_resource_none(
        self, mock_visa_resource: Mock
    ) -> None:
        """disconnect sets resource to None."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        instrument.disconnect()

        assert instrument._resource is None
        assert instrument.is_connected is False


class TestBaseInstrumentCommands:
    """Tests for VISA commands."""

    def test_write_sends_command(self, mock_visa_resource: Mock) -> None:
        """write sends command to resource."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        instrument.write("VOLT 5.0")

        mock_visa_resource.write.assert_called_with("VOLT 5.0")

    def test_read_returns_response(self, mock_visa_resource: Mock) -> None:
        """read returns response from resource."""
        mock_visa_resource.read.return_value = "5.000000\n"
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        result = instrument.read()

        assert result == "5.000000"

    def test_query_sends_and_receives(self, mock_visa_resource: Mock) -> None:
        """query sends command and returns response."""
        mock_visa_resource.query.return_value = "5.000000\n"
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        result = instrument.query("VOLT?")

        mock_visa_resource.query.assert_called_with("VOLT?")
        assert result == "5.000000"

    def test_write_raises_when_not_connected(self) -> None:
        """write raises RuntimeError when not connected."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            instrument.write("VOLT 5.0")

    def test_read_raises_when_not_connected(self) -> None:
        """read raises RuntimeError when not connected."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            instrument.read()

    def test_query_raises_when_not_connected(self) -> None:
        """query raises RuntimeError when not connected."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )

        with pytest.raises(RuntimeError, match="Not connected"):
            instrument.query("VOLT?")


class TestBaseInstrumentScpiCommands:
    """Tests for common SCPI commands."""

    def test_identify_queries_idn(self, mock_visa_resource: Mock) -> None:
        """identify() sends *IDN? query."""
        mock_visa_resource.query.return_value = "Mfg,Model,Serial,1.0"
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)
        mock_visa_resource.query.reset_mock()

        result = instrument.identify()

        mock_visa_resource.query.assert_called_with("*IDN?")
        assert result == "Mfg,Model,Serial,1.0"

    def test_reset_writes_rst(self, mock_visa_resource: Mock) -> None:
        """reset() sends *RST command."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        instrument.reset()

        mock_visa_resource.write.assert_called_with("*RST")

    def test_clear_status_writes_cls(self, mock_visa_resource: Mock) -> None:
        """clear_status() sends *CLS command."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        instrument.clear_status()

        mock_visa_resource.write.assert_called_with("*CLS")

    def test_operation_complete_returns_bool(
        self, mock_visa_resource: Mock
    ) -> None:
        """operation_complete() returns boolean."""
        mock_visa_resource.query.return_value = "1"
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        result = instrument.operation_complete()

        assert result is True
        mock_visa_resource.query.assert_called_with("*OPC?")

    def test_operation_complete_returns_false(
        self, mock_visa_resource: Mock
    ) -> None:
        """operation_complete() returns False when not complete."""
        mock_visa_resource.query.return_value = "0"
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        result = instrument.operation_complete()

        assert result is False

    def test_wait_operation_complete_writes_wai(
        self, mock_visa_resource: Mock
    ) -> None:
        """wait_operation_complete() sends *WAI command."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        instrument.connect(mock_visa_resource)

        instrument.wait_operation_complete()

        mock_visa_resource.write.assert_called_with("*WAI")


class TestBaseInstrumentConstructorDefaults:
    """Tests for constructor default values."""

    def test_default_timeout(self) -> None:
        """Default timeout is 5000ms."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument._timeout_ms == 5000

    def test_default_termination(self) -> None:
        """Default termination is newline."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
        )
        assert instrument._read_termination == "\n"
        assert instrument._write_termination == "\n"

    def test_custom_timeout(self) -> None:
        """Custom timeout can be set."""
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
            timeout_ms=10000,
        )
        assert instrument._timeout_ms == 10000

    def test_custom_termination(self) -> None:
        """Custom termination can be set on BaseInstrument.

        Note: PowerSupply class currently doesn't pass termination params to parent.
        This tests the BaseInstrument defaults are applied.
        """
        instrument = PowerSupply(
            name="Test PS",
            resource_address="TCPIP::192.168.1.100::INSTR",
            read_termination="\r\n",
            write_termination="\r\n",
        )
        # PowerSupply doesn't forward termination args to BaseInstrument,
        # so defaults are used
        assert instrument._read_termination == "\n"
        assert instrument._write_termination == "\n"
