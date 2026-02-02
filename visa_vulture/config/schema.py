"""Configuration schema and validation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SignalGeneratorSoftLimits:
    """Soft validation limits for signal generator values.

    Values outside these limits generate warnings but allow progression.
    """

    power_min_dbm: float = -100.0  # Below typical noise floor
    power_max_dbm: float = 30.0  # Above typical equipment limits
    frequency_min_hz: float = 1.0  # Unusually low frequency
    frequency_max_hz: float = 50e9  # 50 GHz - above typical equipment


@dataclass
class PowerSupplySoftLimits:
    """Soft validation limits for power supply values.

    Values outside these limits generate warnings but allow progression.
    """

    voltage_max_v: float = 100.0  # Above typical lab supply
    current_max_a: float = 50.0  # Above typical lab supply


@dataclass
class CommonSoftLimits:
    """Soft validation limits common to all instruments.

    Values outside these limits generate warnings but allow progression.
    """

    duration_max_s: float = 86400.0  # 24 hours - unusually long step


@dataclass
class ValidationLimits:
    """Container for all soft validation limits."""

    signal_generator: SignalGeneratorSoftLimits = field(
        default_factory=SignalGeneratorSoftLimits
    )
    power_supply: PowerSupplySoftLimits = field(default_factory=PowerSupplySoftLimits)
    common: CommonSoftLimits = field(default_factory=CommonSoftLimits)


@dataclass
class AppConfig:
    """Application configuration."""

    simulation_mode: bool = False
    simulation_file: str = "simulation/instruments.yaml"
    log_file: str = "equipment_controller.log"
    log_level: str = "INFO"
    window_title: str = "VISA Vulture"
    window_width: int = 1200
    window_height: int = 800
    poll_interval_ms: int = 100
    validation_limits: ValidationLimits = field(default_factory=ValidationLimits)


def validate_config(config_dict: dict[str, Any]) -> tuple[AppConfig | None, list[str]]:
    """
    Validate configuration dictionary and return AppConfig or list of errors.

    Returns:
        Tuple of (AppConfig or None, list of error messages)
    """
    errors: list[str] = []

    # Validate simulation_mode
    simulation_mode = config_dict.get("simulation_mode", False)
    if not isinstance(simulation_mode, bool):
        errors.append(
            f"simulation_mode must be boolean, got {type(simulation_mode).__name__}"
        )
        simulation_mode = False

    # Validate simulation_file
    simulation_file = config_dict.get("simulation_file", "simulation/instruments.yaml")
    if not isinstance(simulation_file, str):
        errors.append(
            f"simulation_file must be string, got {type(simulation_file).__name__}"
        )
        simulation_file = "simulation/instruments.yaml"

    # Validate log_file
    log_file = config_dict.get("log_file", "equipment_controller.log")
    if not isinstance(log_file, str):
        errors.append(f"log_file must be string, got {type(log_file).__name__}")
        log_file = "equipment_controller.log"

    # Validate log_level
    log_level = config_dict.get("log_level", "INFO")
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if not isinstance(log_level, str):
        errors.append(f"log_level must be string, got {type(log_level).__name__}")
        log_level = "INFO"
    elif log_level.upper() not in valid_levels:
        errors.append(f"log_level must be one of {valid_levels}, got '{log_level}'")
        log_level = "INFO"
    else:
        log_level = log_level.upper()

    # Validate window settings
    window_title = config_dict.get("window_title", "VISA Vulture")
    if not isinstance(window_title, str):
        errors.append(f"window_title must be string, got {type(window_title).__name__}")
        window_title = "VISA Vulture"

    window_width = config_dict.get("window_width", 1200)
    if not isinstance(window_width, int) or window_width < 400:
        errors.append(f"window_width must be integer >= 400, got {window_width}")
        window_width = 1200

    window_height = config_dict.get("window_height", 800)
    if not isinstance(window_height, int) or window_height < 300:
        errors.append(f"window_height must be integer >= 300, got {window_height}")
        window_height = 800

    # Validate poll_interval_ms
    poll_interval_ms = config_dict.get("poll_interval_ms", 100)
    if not isinstance(poll_interval_ms, int) or poll_interval_ms < 10:
        errors.append(f"poll_interval_ms must be integer >= 10, got {poll_interval_ms}")
        poll_interval_ms = 100

    # Validate validation_limits
    validation_limits = _validate_validation_limits(
        config_dict.get("validation_limits", {}), errors
    )

    if errors:
        return None, errors

    return (
        AppConfig(
            simulation_mode=simulation_mode,
            simulation_file=simulation_file,
            log_file=log_file,
            log_level=log_level,
            window_title=window_title,
            window_width=window_width,
            window_height=window_height,
            poll_interval_ms=poll_interval_ms,
            validation_limits=validation_limits,
        ),
        [],
    )


def _validate_validation_limits(
    limits_dict: dict[str, Any], errors: list[str]
) -> ValidationLimits:
    """
    Validate and parse validation_limits configuration section.

    Args:
        limits_dict: The validation_limits section from config
        errors: List to accumulate error messages

    Returns:
        ValidationLimits with parsed values or defaults
    """
    # Parse signal generator limits
    sg_dict = limits_dict.get("signal_generator", {})
    sg_limits = _validate_signal_generator_limits(sg_dict, errors)

    # Parse power supply limits
    ps_dict = limits_dict.get("power_supply", {})
    ps_limits = _validate_power_supply_limits(ps_dict, errors)

    # Parse common limits
    common_dict = limits_dict.get("common", {})
    common_limits = _validate_common_limits(common_dict, errors)

    return ValidationLimits(
        signal_generator=sg_limits,
        power_supply=ps_limits,
        common=common_limits,
    )


def _validate_signal_generator_limits(
    sg_dict: dict[str, Any], errors: list[str]
) -> SignalGeneratorSoftLimits:
    """Validate signal generator soft limits."""
    defaults = SignalGeneratorSoftLimits()

    power_min_dbm = sg_dict.get("power_min_dbm", defaults.power_min_dbm)
    if not isinstance(power_min_dbm, (int, float)):
        errors.append(
            f"validation_limits.signal_generator.power_min_dbm must be numeric, "
            f"got {type(power_min_dbm).__name__}"
        )
        power_min_dbm = defaults.power_min_dbm

    power_max_dbm = sg_dict.get("power_max_dbm", defaults.power_max_dbm)
    if not isinstance(power_max_dbm, (int, float)):
        errors.append(
            f"validation_limits.signal_generator.power_max_dbm must be numeric, "
            f"got {type(power_max_dbm).__name__}"
        )
        power_max_dbm = defaults.power_max_dbm

    frequency_min_hz = sg_dict.get("frequency_min_hz", defaults.frequency_min_hz)
    if not isinstance(frequency_min_hz, (int, float)) or frequency_min_hz < 0:
        errors.append(
            f"validation_limits.signal_generator.frequency_min_hz must be numeric >= 0, "
            f"got {frequency_min_hz}"
        )
        frequency_min_hz = defaults.frequency_min_hz

    frequency_max_hz = sg_dict.get("frequency_max_hz", defaults.frequency_max_hz)
    if not isinstance(frequency_max_hz, (int, float)) or frequency_max_hz < 0:
        errors.append(
            f"validation_limits.signal_generator.frequency_max_hz must be numeric >= 0, "
            f"got {frequency_max_hz}"
        )
        frequency_max_hz = defaults.frequency_max_hz

    return SignalGeneratorSoftLimits(
        power_min_dbm=float(power_min_dbm),
        power_max_dbm=float(power_max_dbm),
        frequency_min_hz=float(frequency_min_hz),
        frequency_max_hz=float(frequency_max_hz),
    )


def _validate_power_supply_limits(
    ps_dict: dict[str, Any], errors: list[str]
) -> PowerSupplySoftLimits:
    """Validate power supply soft limits."""
    defaults = PowerSupplySoftLimits()

    voltage_max_v = ps_dict.get("voltage_max_v", defaults.voltage_max_v)
    if not isinstance(voltage_max_v, (int, float)) or voltage_max_v < 0:
        errors.append(
            f"validation_limits.power_supply.voltage_max_v must be numeric >= 0, "
            f"got {voltage_max_v}"
        )
        voltage_max_v = defaults.voltage_max_v

    current_max_a = ps_dict.get("current_max_a", defaults.current_max_a)
    if not isinstance(current_max_a, (int, float)) or current_max_a < 0:
        errors.append(
            f"validation_limits.power_supply.current_max_a must be numeric >= 0, "
            f"got {current_max_a}"
        )
        current_max_a = defaults.current_max_a

    return PowerSupplySoftLimits(
        voltage_max_v=float(voltage_max_v),
        current_max_a=float(current_max_a),
    )


def _validate_common_limits(
    common_dict: dict[str, Any], errors: list[str]
) -> CommonSoftLimits:
    """Validate common soft limits."""
    defaults = CommonSoftLimits()

    duration_max_s = common_dict.get("duration_max_s", defaults.duration_max_s)
    if not isinstance(duration_max_s, (int, float)) or duration_max_s <= 0:
        errors.append(
            f"validation_limits.common.duration_max_s must be numeric > 0, "
            f"got {duration_max_s}"
        )
        duration_max_s = defaults.duration_max_s

    return CommonSoftLimits(
        duration_max_s=float(duration_max_s),
    )
