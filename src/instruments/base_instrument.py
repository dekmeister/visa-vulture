"""Base instrument class with common SCPI functionality."""

import logging
from abc import ABC, abstractmethod

import pyvisa

logger = logging.getLogger(__name__)


class BaseInstrument(ABC):
    """
    Abstract base class for VISA instruments.

    Provides common SCPI commands and connection management.
    Subclasses implement instrument-specific functionality.
    """

    def __init__(
        self,
        name: str,
        resource_address: str,
        timeout_ms: int = 5000,
        read_termination: str | None = "\n",
        write_termination: str | None = "\n",
    ):
        """
        Initialize instrument.

        Args:
            name: Human-readable instrument name
            resource_address: VISA resource address
            timeout_ms: Communication timeout in milliseconds
            read_termination: Character(s) appended to reads, or None for no termination
            write_termination: Character(s) appended to writes, or None for no termination
        """
        self._name = name
        self._resource_address = resource_address
        self._timeout_ms = timeout_ms
        self._read_termination = read_termination
        self._write_termination = write_termination
        self._resource: pyvisa.resources.MessageBasedResource | None = None
        self._identification: str | None = None

    @property
    def name(self) -> str:
        """Get instrument name."""
        return self._name

    @property
    def resource_address(self) -> str:
        """Get VISA resource address."""
        return self._resource_address

    @property
    def is_connected(self) -> bool:
        """Check if instrument is connected."""
        return self._resource is not None

    @property
    def identification(self) -> str | None:
        """Get the raw identification string from *IDN? query."""
        return self._identification

    def manufacturer(self) -> str:
        """
        Parse manufacturer from *IDN? response.

        Returns:
            Manufacturer name or "Unknown" if not available
        """
        if not self._identification:
            return "Unknown"
        parts = self._identification.split(",")
        return parts[0].strip() if len(parts) >= 1 and parts[0].strip() else "Unknown"

    def model(self) -> str:
        """
        Parse model from *IDN? response.

        Returns:
            Model name or "Unknown" if not available
        """
        if not self._identification:
            return "Unknown"
        parts = self._identification.split(",")
        return parts[1].strip() if len(parts) >= 2 and parts[1].strip() else "Unknown"

    def serial(self) -> str:
        """
        Parse serial number from *IDN? response.

        Returns:
            Serial number or "Unknown" if not available
        """
        if not self._identification:
            return "Unknown"
        parts = self._identification.split(",")
        return parts[2].strip() if len(parts) >= 3 and parts[2].strip() else "Unknown"

    def firmware(self) -> str:
        """
        Parse firmware version from *IDN? response.

        Returns:
            Firmware version or "Unknown" if not available
        """
        if not self._identification:
            return "Unknown"
        parts = self._identification.split(",")
        return parts[3].strip() if len(parts) >= 4 and parts[3].strip() else "Unknown"

    def formatted_identification(self) -> str:
        """
        Return human-readable formatted identification for tooltip display.

        Returns:
            Formatted identification string
        """
        return (
            f"Manufacturer: {self.manufacturer()}\n"
            f"Model: {self.model()}\n"
            f"Serial: {self.serial()}\n"
            f"Firmware: {self.firmware()}"
        )

    def connect(self, visa_resource: pyvisa.resources.MessageBasedResource) -> None:
        """
        Connect to the instrument.

        Args:
            visa_resource: Opened VISA resource from VISAConnection
        """
        if self._resource is not None:
            logger.warning("%s: Already connected", self._name)
            return

        self._resource = visa_resource
        logger.info("%s: Connected to %s", self._name, self._resource_address)

        # Query identification
        try:
            idn = self.identify()
            self._identification = idn
            logger.info("%s: Identification: %s", self._name, idn)
        except Exception as e:
            logger.warning("%s: Could not query identification: %s", self._name, e)

    def disconnect(self) -> None:
        """Disconnect from the instrument."""
        if self._resource is not None:
            try:
                self._resource.close()
            except Exception as e:
                logger.warning("%s: Error closing resource: %s", self._name, e)
            finally:
                self._resource = None
                logger.info("%s: Disconnected", self._name)

    def _check_connected(self) -> None:
        """Raise exception if not connected."""
        if self._resource is None:
            raise RuntimeError(f"{self._name}: Not connected")

    def write(self, command: str) -> None:
        """
        Send a command to the instrument.

        Args:
            command: SCPI command string
        """
        self._check_connected()
        assert self._resource is not None  # Type narrowing: _check_connected ensures this
        logger.debug("%s: Write: %s", self._name, command)
        self._resource.write(command)

    def read(self) -> str:
        """
        Read response from the instrument.

        Returns:
            Response string
        """
        self._check_connected()
        assert self._resource is not None  # Type narrowing: _check_connected ensures this
        response = self._resource.read().strip()
        logger.debug("%s: Read: %s", self._name, response)
        return response

    def query(self, command: str) -> str:
        """
        Send a command and read the response.

        Args:
            command: SCPI command string

        Returns:
            Response string
        """
        self._check_connected()
        assert self._resource is not None  # Type narrowing: _check_connected ensures this
        logger.debug("%s: Query: %s", self._name, command)
        response = self._resource.query(command).strip()
        logger.debug("%s: Response: %s", self._name, response)
        return response

    # Common SCPI commands

    def identify(self) -> str:
        """
        Query instrument identification (*IDN?).

        Returns:
            Identification string (manufacturer, model, serial, firmware)
        """
        return self.query("*IDN?")

    def reset(self) -> None:
        """Reset instrument to default state (*RST)."""
        logger.info("%s: Resetting instrument", self._name)
        self.write("*RST")

    def clear_status(self) -> None:
        """Clear status registers (*CLS)."""
        self.write("*CLS")

    def operation_complete(self) -> bool:
        """
        Query operation complete status (*OPC?).

        Returns:
            True if all pending operations are complete
        """
        response = self.query("*OPC?")
        return response == "1"

    def wait_operation_complete(self) -> None:
        """Wait for all pending operations to complete (*WAI)."""
        self.write("*WAI")

    @abstractmethod
    def get_status(self) -> dict:
        """
        Get instrument-specific status information.

        Returns:
            Dictionary of status values
        """
        pass
