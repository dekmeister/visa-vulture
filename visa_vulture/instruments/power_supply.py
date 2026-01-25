"""Power supply instrument implementation."""

import logging

from .base_instrument import BaseInstrument

logger = logging.getLogger(__name__)


class PowerSupply(BaseInstrument):
    """
    Power supply instrument with voltage and current control.

    Implements common power supply SCPI commands.
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
        Initialize power supply.

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
        Get power supply status.

        Returns:
            Dictionary with voltage, current, and output state
        """
        self._check_connected()
        return {
            "voltage": self.get_voltage(),
            "current": self.get_current(),
            "output_enabled": self.is_output_enabled(),
        }

    # Voltage control

    def set_voltage(self, voltage: float) -> None:
        """
        Set output voltage.

        Args:
            voltage: Voltage in volts
        """
        self._check_connected()
        logger.info("%s: Setting voltage to %.3f V", self._name, voltage)
        self.write(f"VOLT {voltage:.6f}")

    def get_voltage(self) -> float:
        """
        Get current voltage setpoint.

        Returns:
            Voltage setpoint in volts
        """
        self._check_connected()
        response = self.query("VOLT?")
        return float(response)

    def measure_voltage(self) -> float:
        """
        Measure actual output voltage.

        Returns:
            Measured voltage in volts
        """
        self._check_connected()
        response = self.query("MEAS:VOLT?")
        return float(response)

    # Current control

    def set_current(self, current: float) -> None:
        """
        Set current limit.

        Args:
            current: Current limit in amps
        """
        self._check_connected()
        logger.info("%s: Setting current limit to %.3f A", self._name, current)
        self.write(f"CURR {current:.6f}")

    def get_current(self) -> float:
        """
        Get current limit setpoint.

        Returns:
            Current limit in amps
        """
        self._check_connected()
        response = self.query("CURR?")
        return float(response)

    def measure_current(self) -> float:
        """
        Measure actual output current.

        Returns:
            Measured current in amps
        """
        self._check_connected()
        response = self.query("MEAS:CURR?")
        return float(response)

    # Output control

    def enable_output(self) -> None:
        """Enable power supply output."""
        self._check_connected()
        logger.info("%s: Enabling output", self._name)
        self.write("OUTP ON")

    def disable_output(self) -> None:
        """Disable power supply output."""
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

    # Power measurement

    def measure_power(self) -> float:
        """
        Calculate power from measured voltage and current.

        Returns:
            Power in watts
        """
        voltage = self.measure_voltage()
        current = self.measure_current()
        return voltage * current
