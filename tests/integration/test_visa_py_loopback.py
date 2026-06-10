"""Integration tests for the real VISA backend over a genuine TCP transport.

These tests use the pyvisa-py backend ("@py") to open a TCPIP SOCKET resource
against a local loopback server, exchanging real bytes over an OS socket.
Unlike the pyvisa-sim tests, this exercises the actual transport path:
backend selection, resource opening, terminator framing over a byte stream,
and timeout behaviour.
"""

import time

import pytest

pytest.importorskip("pyvisa_py")

import pyvisa
import pyvisa.errors

from tests.integration.scpi_loopback import ScpiLoopbackServer
from visa_vulture.instruments import PowerSupply, VISAConnection
from visa_vulture.main import validate_visa_backend
from visa_vulture.model import EquipmentModel, EquipmentState

IDN_RESPONSE = b"LoopMfg,LoopModel,0001,1.0"

DEFAULT_RESPONSES = {
    b"*IDN?": IDN_RESPONSE,
    b"VOLT?": b"5.000000",
    b"MEAS:VOLT?": b"4.998000",
}


@pytest.fixture
def loopback_server():
    """Loopback SCPI server with a canned response table."""
    with ScpiLoopbackServer(DEFAULT_RESPONSES) as server:
        yield server


@pytest.fixture
def visa_connection_py():
    """Real VISAConnection using the pyvisa-py backend."""
    conn = VISAConnection(visa_backend="py")
    yield conn
    if conn.is_open:
        conn.close()


@pytest.mark.integration
class TestPyBackendLoadable:
    """The real-backend code path loads with pyvisa-py installed."""

    def test_resource_manager_opens_py_backend(self):
        rm = pyvisa.ResourceManager("@py")
        try:
            assert type(rm.visalib).__module__.startswith("pyvisa_py")
        finally:
            rm.close()

    def test_validate_visa_backend_accepts_py(self):
        assert validate_visa_backend("py") is None

    def test_visa_connection_active_backend_is_py(self, visa_connection_py):
        visa_connection_py.open()
        assert visa_connection_py.is_open
        assert visa_connection_py.active_backend == "py"


@pytest.mark.integration
class TestSocketRoundTrip:
    """Round-trip communication over a real TCP socket."""

    def test_query_round_trip(self, visa_connection_py, loopback_server):
        visa_connection_py.open()
        resource = visa_connection_py.open_resource(loopback_server.resource_address)
        try:
            response = resource.query("*IDN?")
            assert response == IDN_RESPONSE.decode()
        finally:
            resource.close()

    def test_default_write_termination_on_wire(
        self, visa_connection_py, loopback_server
    ):
        visa_connection_py.open()
        resource = visa_connection_py.open_resource(loopback_server.resource_address)
        try:
            resource.query("*IDN?")
            # The completed read guarantees the server has consumed the command
            assert loopback_server.received_bytes() == b"*IDN?\n"
        finally:
            resource.close()

    def test_custom_write_termination_on_wire(self, visa_connection_py):
        with ScpiLoopbackServer(
            DEFAULT_RESPONSES, command_termination=b"\r\n"
        ) as server:
            visa_connection_py.open()
            resource = visa_connection_py.open_resource(
                server.resource_address,
                read_termination="\n",
                write_termination="\r\n",
            )
            try:
                resource.query("*IDN?")
                assert server.received_bytes().endswith(b"*IDN?\r\n")
            finally:
                resource.close()

    def test_read_termination_stripped(self, visa_connection_py, loopback_server):
        visa_connection_py.open()
        resource = visa_connection_py.open_resource(loopback_server.resource_address)
        try:
            response = resource.query("VOLT?")
            assert response == "5.000000"
            assert not response.endswith("\n")
        finally:
            resource.close()

    def test_timeout_raises_visa_io_error(self, visa_connection_py, loopback_server):
        visa_connection_py.open()
        resource = visa_connection_py.open_resource(
            loopback_server.resource_address, timeout_ms=300
        )
        try:
            start = time.monotonic()
            with pytest.raises(pyvisa.errors.VisaIOError) as exc_info:
                resource.query("NOPE?")
            elapsed = time.monotonic() - start
            assert (
                exc_info.value.error_code == pyvisa.constants.StatusCode.error_timeout
            )
            # Failing well under pyvisa's 2000ms default proves the configured
            # timeout was applied to the resource
            assert elapsed < 1.5
        finally:
            resource.close()


class CrlfPowerSupply(PowerSupply):
    """Power supply using CRLF write termination, for terminator forwarding tests."""

    display_name = "CRLF Power Supply"

    def __init__(self, name: str, resource_address: str, timeout_ms: int = 5000):
        super().__init__(
            name,
            resource_address,
            timeout_ms,
            read_termination="\n",
            write_termination="\r\n",
        )


@pytest.mark.integration
class TestEquipmentModelOverRealTransport:
    """Production connect path (EquipmentModel) over a real socket transport."""

    def test_connect_instrument_round_trip(self, loopback_server):
        conn = VISAConnection(visa_backend="py")
        model = EquipmentModel(conn)
        try:
            model.connect_instrument(loopback_server.resource_address, "power_supply")
            assert model.state == EquipmentState.IDLE
            assert model.instrument is not None
            assert model.instrument.manufacturer() == "LoopMfg"

            model.instrument.set_voltage(5.0)
            assert model.instrument.get_voltage() == pytest.approx(5.0)
        finally:
            model.disconnect()
            conn.close()

    def test_instrument_terminators_forwarded_to_resource(self):
        with ScpiLoopbackServer(
            DEFAULT_RESPONSES, command_termination=b"\r\n"
        ) as server:
            conn = VISAConnection(visa_backend="py")
            model = EquipmentModel(conn)
            try:
                # Connect queries *IDN?; it only succeeds if the instrument's
                # CRLF write terminator is forwarded to the opened resource
                model.connect_instrument(
                    server.resource_address,
                    "power_supply",
                    instrument_class=CrlfPowerSupply,
                )
                assert server.received_bytes().endswith(b"*IDN?\r\n")
                assert model.instrument is not None
                assert model.instrument.manufacturer() == "LoopMfg"
            finally:
                model.disconnect()
                conn.close()


@pytest.mark.integration
class TestPowerSupplyOverRealTransport:
    """Full instrument stack over a real socket transport."""

    def test_power_supply_connect_set_and_measure(
        self, visa_connection_py, loopback_server
    ):
        visa_connection_py.open()
        resource = visa_connection_py.open_resource(loopback_server.resource_address)
        ps = PowerSupply("Loopback PS", loopback_server.resource_address)
        ps.connect(resource)
        try:
            assert ps.is_connected
            assert ps.manufacturer() == "LoopMfg"
            assert ps.model() == "LoopModel"

            ps.set_voltage(5.0)
            assert ps.get_voltage() == pytest.approx(5.0)
            # The completed query above guarantees the server has consumed
            # the preceding write
            assert b"VOLT 5.000000" in loopback_server.received_commands()
            assert ps.measure_voltage() == pytest.approx(4.998)
        finally:
            ps.disconnect()
