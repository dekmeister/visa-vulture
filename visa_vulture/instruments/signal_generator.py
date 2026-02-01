"""Signal generator instrument implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_instrument import BaseInstrument

if TYPE_CHECKING:
    from visa_vulture.model.test_plan import (
        ModulationConfig,
        AMModulationConfig,
        FMModulationConfig,
        ModulationType,
    )

logger = logging.getLogger(__name__)


class SignalGenerator(BaseInstrument):
    """
    Signal generator instrument with frequency, power, and modulation control.

    Implements common signal generator SCPI commands including AM and FM modulation.
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
            Dictionary with frequency, power, output state, and modulation state
        """
        self._check_connected()
        return {
            "frequency": self.get_frequency(),
            "power": self.get_power(),
            "output_enabled": self.is_output_enabled(),
            "am_enabled": self.is_am_enabled(),
            "fm_enabled": self.is_fm_enabled(),
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

    # AM Modulation control

    def configure_am_modulation(
        self,
        modulation_frequency: float,
        depth: float,
    ) -> None:
        """
        Configure AM modulation parameters.

        Args:
            modulation_frequency: Internal modulating signal frequency in Hz
            depth: Modulation depth as percentage (0-100)
        """
        self._check_connected()
        logger.info(
            "%s: Configuring AM: freq=%.1f Hz, depth=%.1f%%",
            self._name,
            modulation_frequency,
            depth,
        )
        # Set internal modulation source
        self.write("AM:SOUR INT")
        # Set modulating frequency
        self.write(f"AM:INT:FREQ {modulation_frequency:.1f}")
        # Set modulation depth
        self.write(f"AM:DEPT {depth:.1f}")

    def enable_am_modulation(self) -> None:
        """Enable AM modulation output."""
        self._check_connected()
        logger.info("%s: Enabling AM modulation", self._name)
        self.write("AM:STAT ON")

    def disable_am_modulation(self) -> None:
        """Disable AM modulation output."""
        self._check_connected()
        logger.info("%s: Disabling AM modulation", self._name)
        self.write("AM:STAT OFF")

    def is_am_enabled(self) -> bool:
        """
        Check if AM modulation is enabled.

        Returns:
            True if AM modulation is enabled
        """
        self._check_connected()
        response = self.query("AM:STAT?")
        return response in ("1", "ON")

    # FM Modulation control

    def configure_fm_modulation(
        self,
        modulation_frequency: float,
        deviation: float,
    ) -> None:
        """
        Configure FM modulation parameters.

        Args:
            modulation_frequency: Internal modulating signal frequency in Hz
            deviation: Frequency deviation in Hz
        """
        self._check_connected()
        logger.info(
            "%s: Configuring FM: freq=%.1f Hz, deviation=%.1f Hz",
            self._name,
            modulation_frequency,
            deviation,
        )
        # Set internal modulation source
        self.write("FM:SOUR INT")
        # Set modulating frequency
        self.write(f"FM:INT:FREQ {modulation_frequency:.1f}")
        # Set deviation
        self.write(f"FM:DEV {deviation:.1f}")

    def enable_fm_modulation(self) -> None:
        """Enable FM modulation output."""
        self._check_connected()
        logger.info("%s: Enabling FM modulation", self._name)
        self.write("FM:STAT ON")

    def disable_fm_modulation(self) -> None:
        """Disable FM modulation output."""
        self._check_connected()
        logger.info("%s: Disabling FM modulation", self._name)
        self.write("FM:STAT OFF")

    def is_fm_enabled(self) -> bool:
        """
        Check if FM modulation is enabled.

        Returns:
            True if FM modulation is enabled
        """
        self._check_connected()
        response = self.query("FM:STAT?")
        return response in ("1", "ON")

    # Generic modulation control

    def configure_modulation(self, config: ModulationConfig) -> None:
        """
        Configure modulation from a ModulationConfig object.

        This is a convenience method that dispatches to the appropriate
        type-specific configuration method.

        Args:
            config: Modulation configuration object
        """
        # Import here to avoid circular imports at module level
        from visa_vulture.model.test_plan import (
            AMModulationConfig,
            FMModulationConfig,
        )

        if isinstance(config, AMModulationConfig):
            self.configure_am_modulation(config.modulation_frequency, config.depth)
        elif isinstance(config, FMModulationConfig):
            self.configure_fm_modulation(config.modulation_frequency, config.deviation)
        else:
            raise ValueError(f"Unsupported modulation config type: {type(config)}")

    def set_modulation_enabled(
        self,
        config: ModulationConfig,
        enabled: bool,
    ) -> None:
        """
        Enable or disable modulation based on config type.

        Args:
            config: Modulation configuration (determines which modulation type)
            enabled: Whether to enable or disable modulation
        """
        from visa_vulture.model.test_plan import ModulationType

        if config.modulation_type == ModulationType.AM:
            if enabled:
                self.enable_am_modulation()
            else:
                self.disable_am_modulation()
        elif config.modulation_type == ModulationType.FM:
            if enabled:
                self.enable_fm_modulation()
            else:
                self.disable_fm_modulation()

    def disable_all_modulation(self) -> None:
        """Disable all modulation types."""
        self._check_connected()
        logger.info("%s: Disabling all modulation", self._name)
        self.write("AM:STAT OFF")
        self.write("FM:STAT OFF")
