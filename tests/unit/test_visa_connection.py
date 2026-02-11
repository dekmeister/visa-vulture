"""Tests for VISAConnection."""

from unittest.mock import Mock, patch

import pyvisa.resources

from visa_vulture.instruments.visa_connection import VISAConnection


def _make_connection_with_mock_rm() -> tuple[VISAConnection, Mock]:
    """Create a VISAConnection with a mock resource manager injected.

    Returns the connection and the mock resource that open_resource() will return.
    """
    conn = VISAConnection()
    mock_resource = Mock(spec=pyvisa.resources.MessageBasedResource)
    mock_rm = Mock()
    mock_rm.open_resource.return_value = mock_resource
    conn._resource_manager = mock_rm
    return conn, mock_resource


class TestOpenResourceTermination:
    """Tests for read/write termination handling in open_resource()."""

    def test_sets_write_termination_to_default(self) -> None:
        """Default write_termination='\\n' is applied to the resource."""
        conn, resource = _make_connection_with_mock_rm()
        result = conn.open_resource("TCPIP::1.2.3.4::INSTR")
        assert result.write_termination == "\n"

    def test_sets_read_termination_to_default(self) -> None:
        """Default read_termination='\\n' is applied to the resource."""
        conn, resource = _make_connection_with_mock_rm()
        result = conn.open_resource("TCPIP::1.2.3.4::INSTR")
        assert result.read_termination == "\n"

    def test_sets_custom_write_termination(self) -> None:
        """Custom write_termination value is applied to the resource."""
        conn, resource = _make_connection_with_mock_rm()
        conn.open_resource("TCPIP::1.2.3.4::INSTR", write_termination="\r\n")
        assert resource.write_termination == "\r\n"

    def test_sets_custom_read_termination(self) -> None:
        """Custom read_termination value is applied to the resource."""
        conn, resource = _make_connection_with_mock_rm()
        conn.open_resource("TCPIP::1.2.3.4::INSTR", read_termination="\r\n")
        assert resource.read_termination == "\r\n"

    def test_skips_write_termination_when_none(self) -> None:
        """write_termination=None means the attribute is not set on the resource."""
        conn, resource = _make_connection_with_mock_rm()
        sentinel = object()
        resource.write_termination = sentinel
        conn.open_resource("TCPIP::1.2.3.4::INSTR", write_termination=None)
        assert resource.write_termination is sentinel

    def test_skips_read_termination_when_none(self) -> None:
        """read_termination=None means the attribute is not set on the resource."""
        conn, resource = _make_connection_with_mock_rm()
        sentinel = object()
        resource.read_termination = sentinel
        conn.open_resource("TCPIP::1.2.3.4::INSTR", read_termination=None)
        assert resource.read_termination is sentinel


class TestOpenResourceTimeout:
    """Tests for timeout handling in open_resource()."""

    def test_sets_timeout(self) -> None:
        """timeout_ms is applied to the resource."""
        conn, resource = _make_connection_with_mock_rm()
        conn.open_resource("TCPIP::1.2.3.4::INSTR", timeout_ms=10000)
        assert resource.timeout == 10000

    def test_sets_default_timeout(self) -> None:
        """Default timeout of 5000ms is applied when not specified."""
        conn, resource = _make_connection_with_mock_rm()
        conn.open_resource("TCPIP::1.2.3.4::INSTR")
        assert resource.timeout == 5000


class TestActiveBackend:
    """Tests for active_backend property."""

    def test_returns_default_when_empty(self) -> None:
        """active_backend returns 'default' when visa_backend is empty."""
        conn = VISAConnection()
        assert conn.active_backend == "default"

    def test_returns_backend_name_when_set(self) -> None:
        """active_backend returns backend name when set."""
        conn = VISAConnection(visa_backend="py")
        assert conn.active_backend == "py"

    def test_returns_sim_when_simulation_mode(self) -> None:
        """active_backend returns 'sim' in simulation mode."""
        conn = VISAConnection(simulation_mode=True, simulation_file="test.yaml")
        assert conn.active_backend == "sim"

    def test_simulation_mode_overrides_visa_backend(self) -> None:
        """Simulation mode overrides any visa_backend setting."""
        conn = VISAConnection(
            simulation_mode=True, simulation_file="test.yaml", visa_backend="py"
        )
        assert conn.active_backend == "sim"


class TestOpenWithBackend:
    """Tests for open() with visa_backend parameter."""

    @patch("visa_vulture.instruments.visa_connection.pyvisa.ResourceManager")
    def test_open_with_backend_prefixes_at_sign(self, mock_rm_cls: Mock) -> None:
        """open() passes '@backend' to ResourceManager when backend is set."""
        conn = VISAConnection(visa_backend="py")
        conn.open()
        mock_rm_cls.assert_called_once_with("@py")

    @patch("visa_vulture.instruments.visa_connection.pyvisa.ResourceManager")
    def test_open_without_backend_passes_empty(self, mock_rm_cls: Mock) -> None:
        """open() passes empty string to ResourceManager when no backend."""
        conn = VISAConnection()
        conn.open()
        mock_rm_cls.assert_called_once_with("")
