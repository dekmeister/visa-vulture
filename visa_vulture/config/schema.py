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
    visa_backend: str = ""
    poll_interval_ms: int = 100
    plot_refresh_interval_ms: int = 1000
    validation_limits: ValidationLimits = field(default_factory=ValidationLimits)


def _validate_str_field(
    config_dict: dict[str, Any],
    key: str,
    default: str,
    errors: list[str],
) -> str:
    """Validate a string configuration field."""
    value = config_dict.get(key, default)
    if not isinstance(value, str):
        errors.append(f"{key} must be string, got {type(value).__name__}")
        return default
    return value


def _validate_int_min_field(
    config_dict: dict[str, Any],
    key: str,
    default: int,
    minimum: int,
    errors: list[str],
) -> int:
    """Validate an integer configuration field with a minimum value."""
    value = config_dict.get(key, default)
    if not isinstance(value, int) or value < minimum:
        errors.append(f"{key} must be integer >= {minimum}, got {value}")
        return default
    return value


def _validate_numeric_field(
    source: dict[str, Any],
    key: str,
    default: float,
    errors: list[str],
    prefix: str,
    *,
    min_value: float | None = None,
    min_exclusive: bool = False,
) -> float:
    """Validate a numeric field within a nested configuration section."""
    value = source.get(key, default)

    if min_value is not None:
        op = ">" if min_exclusive else ">="
        constraint = f"numeric {op} {min_value:g}"
    else:
        constraint = "numeric"

    if not isinstance(value, (int, float)):
        if min_value is not None:
            errors.append(f"{prefix}.{key} must be {constraint}, got {value}")
        else:
            errors.append(
                f"{prefix}.{key} must be {constraint}, got {type(value).__name__}"
            )
        return default

    if min_value is not None:
        out_of_range = value <= min_value if min_exclusive else value < min_value
        if out_of_range:
            errors.append(f"{prefix}.{key} must be {constraint}, got {value}")
            return default

    return float(value)


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

    # Validate string fields
    simulation_file = _validate_str_field(
        config_dict, "simulation_file", "simulation/instruments.yaml", errors
    )
    log_file = _validate_str_field(
        config_dict, "log_file", "equipment_controller.log", errors
    )

    # Validate log_level (unique enum logic)
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

    # Validate VISA backend
    visa_backend = _validate_str_field(config_dict, "visa_backend", "", errors)

    # Validate window and interval settings
    window_title = _validate_str_field(
        config_dict, "window_title", "VISA Vulture", errors
    )
    window_width = _validate_int_min_field(
        config_dict, "window_width", 1200, 400, errors
    )
    window_height = _validate_int_min_field(
        config_dict, "window_height", 800, 300, errors
    )
    poll_interval_ms = _validate_int_min_field(
        config_dict, "poll_interval_ms", 100, 10, errors
    )
    plot_refresh_interval_ms = _validate_int_min_field(
        config_dict, "plot_refresh_interval_ms", 1000, 100, errors
    )

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
            visa_backend=visa_backend,
            log_file=log_file,
            log_level=log_level,
            window_title=window_title,
            window_width=window_width,
            window_height=window_height,
            poll_interval_ms=poll_interval_ms,
            plot_refresh_interval_ms=plot_refresh_interval_ms,
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
    prefix = "validation_limits.signal_generator"

    return SignalGeneratorSoftLimits(
        power_min_dbm=_validate_numeric_field(
            sg_dict, "power_min_dbm", defaults.power_min_dbm, errors, prefix
        ),
        power_max_dbm=_validate_numeric_field(
            sg_dict, "power_max_dbm", defaults.power_max_dbm, errors, prefix
        ),
        frequency_min_hz=_validate_numeric_field(
            sg_dict,
            "frequency_min_hz",
            defaults.frequency_min_hz,
            errors,
            prefix,
            min_value=0,
        ),
        frequency_max_hz=_validate_numeric_field(
            sg_dict,
            "frequency_max_hz",
            defaults.frequency_max_hz,
            errors,
            prefix,
            min_value=0,
        ),
    )


def _validate_power_supply_limits(
    ps_dict: dict[str, Any], errors: list[str]
) -> PowerSupplySoftLimits:
    """Validate power supply soft limits."""
    defaults = PowerSupplySoftLimits()
    prefix = "validation_limits.power_supply"

    return PowerSupplySoftLimits(
        voltage_max_v=_validate_numeric_field(
            ps_dict,
            "voltage_max_v",
            defaults.voltage_max_v,
            errors,
            prefix,
            min_value=0,
        ),
        current_max_a=_validate_numeric_field(
            ps_dict,
            "current_max_a",
            defaults.current_max_a,
            errors,
            prefix,
            min_value=0,
        ),
    )


def _validate_common_limits(
    common_dict: dict[str, Any], errors: list[str]
) -> CommonSoftLimits:
    """Validate common soft limits."""
    defaults = CommonSoftLimits()
    prefix = "validation_limits.common"

    return CommonSoftLimits(
        duration_max_s=_validate_numeric_field(
            common_dict,
            "duration_max_s",
            defaults.duration_max_s,
            errors,
            prefix,
            min_value=0,
            min_exclusive=True,
        ),
    )
