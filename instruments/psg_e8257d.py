"""
Keysight PSG E8257D Signal Generator - Example custom instrument extension.

This module demonstrates how to create a custom instrument that extends
an existing instrument type. The PSGE8257D class inherits all standard
signal generator functionality (frequency, power, output, AM/FM modulation)
from the SignalGenerator base class.

Methods from the parent class can be overridden to add instrument-specific
behaviour such as range validation or different SCPI command formats.
Overridden methods like set_frequency and get_frequency are called by the
test plan executor since they replace the parent's implementation.

Usage:
    Place this file in the instruments/ directory at the project root.
    The application will auto-discover it at startup and add it to the
    Resource Manager dialog's instrument type dropdown.
"""

import logging

from visa_vulture.instruments import SignalGenerator

logger = logging.getLogger(__name__)

# E8257D frequency limits
E8257D_MIN_FREQ_HZ = 250e3  # 250 kHz
E8257D_MAX_FREQ_HZ = 67e9  # 67 GHz (Option 567)


class PSGE8257D(SignalGenerator):
    """
    Keysight PSG E8257D Vector Signal Generator.

    Extends the base SignalGenerator with E8257D-specific capabilities.
    All standard signal generator commands (frequency, power, output,
    AM/FM modulation) are inherited and work without modification.

    This example demonstrates overriding set_frequency and get_frequency
    to add instrument-specific range validation and SCPI formatting.
    These overrides are called automatically by the test plan executor
    since they replace the parent methods.

    The display_name class attribute is required and determines how this
    instrument appears in the Resource Manager dialog dropdown.
    """

    display_name = "PSG E8257D"

    # --- Overridden methods ---
    # These replace the parent SignalGenerator methods. The test plan
    # executor calls set_frequency() and get_frequency() during normal
    # operation, so these overrides run automatically.

    def set_frequency(self, frequency_hz: float) -> None:
        """
        Set output frequency with E8257D-specific range validation.

        The E8257D accepts frequencies from 250 kHz to 67 GHz. This
        override validates the range before sending the SCPI command
        and uses the E8257D's higher-precision frequency format.

        Args:
            frequency_hz: Frequency in Hertz (250e3 to 67e9)

        Raises:
            ValueError: If frequency is outside the E8257D's range
        """
        if not E8257D_MIN_FREQ_HZ <= frequency_hz <= E8257D_MAX_FREQ_HZ:
            raise ValueError(
                f"E8257D frequency must be between "
                f"{E8257D_MIN_FREQ_HZ:.0f} Hz and {E8257D_MAX_FREQ_HZ:.0f} Hz, "
                f"got {frequency_hz:.1f} Hz"
            )
        self._check_connected()
        logger.info("%s: Setting frequency to %.6f Hz", self._name, frequency_hz)
        # E8257D supports higher precision frequency setting
        self.write(f"FREQ {frequency_hz:.6f}")

    def get_frequency(self) -> float:
        """
        Get current frequency setpoint.

        Returns:
            Frequency in Hertz
        """
        self._check_connected()
        response = self.query("FREQ?")
        return float(response)

    # --- E8257D-specific methods ---
    #
    # The methods below are examples of instrument-specific functionality
    # that could be added for the E8257D. They are not implemented because
    # the test plan executor does not call custom extension methods during
    # execution. They would be useful when using visa-vulture as a library
    # for direct instrument control.
    #
    # Frequency sweep:
    #   configure_ramp_sweep(start_freq_hz, stop_freq_hz, sweep_time_s)
    #   configure_step_sweep(start_freq_hz, stop_freq_hz, points, dwell_time_s)
    #   start_sweep()
    #   stop_sweep()
    #   get_sweep_status() -> str
    #
    # Pulse modulation:
    #   configure_pulse_modulation(frequency_hz, width_s)
    #   enable_pulse_modulation()
    #   disable_pulse_modulation()
    #   is_pulse_modulation_enabled() -> bool
    #
    # Automatic Leveling Control (ALC):
    #   set_alc_enabled(enabled: bool)
    #   is_alc_enabled() -> bool
    #   set_alc_bandwidth(bandwidth_hz: float)
    #
    # Phase control:
    #   set_phase_offset(degrees: float)
    #   get_phase_offset() -> float
    #   set_phase_reference()
    #
    # Power calibration:
    #   run_power_calibration()
    #   get_calibration_status() -> str
