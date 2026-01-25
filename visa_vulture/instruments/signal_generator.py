"""Signal generator instrument implementation."""

import logging

from .base_instrument import BaseInstrument

logger = logging.getLogger(__name__)


class SignalGenerator(BaseInstrument):
    """
    Signal generator instrument with frequency and power control.

    Implements common signal generator SCPI commands.
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
        Initialize signal generator.

        Args:
            name: Human-readable instrument name
            resource_address: VISA resource address
            timeout_ms: Communication timeout in milliseconds
            read_termination: Character(s) appended to reads, or None for no termination
            write_termination: Character(s) appended to writes, or None for no termination
        """
        super().__init__(name, resource_address, timeout_ms)

    def get_status(self) -> dict:
        """
        Get signal generator status.

        Returns:
            Dictionary with frequency, power, and output state
        """
        self._check_connected()
        return {
            "frequency": self.get_frequency(),
            "power": self.get_power(),
            "output_enabled": self.is_output_enabled(),
        }

    # Frequency control

    def set_frequency(self, frequency_hz: float) -> None:
        """
        Set output frequency.

        Args:
            frequency_hz: Frequency in Hertz
        """
        self._check_connected()
        logger.info("%s: Setting frequency to %.1f Hz", self._name, frequency_hz)
        self.write(f"FREQ {frequency_hz:.1f}")

    def get_frequency(self) -> float:
        """
        Get current frequency setpoint.

        Returns:
            Frequency in Hertz
        """
        self._check_connected()
        response = self.query("FREQ?")
        return float(response)

    # Power control

    def set_power(self, power_dbm: float) -> None:
        """
        Set output power level.

        Args:
            power_dbm: Power in dBm
        """
        self._check_connected()
        logger.info("%s: Setting power to %.2f dBm", self._name, power_dbm)
        self.write(f"POW {power_dbm:.2f}")

    def get_power(self) -> float:
        """
        Get current power setpoint.

        Returns:
            Power in dBm
        """
        self._check_connected()
        response = self.query("POW?")
        return float(response)

    # Output control

    def enable_output(self) -> None:
        """Enable signal generator output."""
        self._check_connected()
        logger.info("%s: Enabling output", self._name)
        self.write("OUTP ON")

    def disable_output(self) -> None:
        """Disable signal generator output."""
        self._check_connected()
        logger.info("%s: Disabling output", self._name)
        self.write("OUTP OFF")

    def is_output_enabled(self) -> bool:
        """
        Check if output is enabled.

        Returns:
            True if output is enabled
        """
        self._check_connected()
        response = self.query("OUTP?")
        return response in ("1", "ON")
