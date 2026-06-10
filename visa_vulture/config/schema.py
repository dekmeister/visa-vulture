"""Configuration schema and validation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommonSoftLimits:
    """Soft validation limits common to all instruments.

    Values outside these limits generate warnings but allow progression.
    """

    duration_max_s: float = 86400.0  # 24 hours - unusually long step


@dataclass
class ValidationLimits:
    """Container for all soft validation limits.

    ``common`` is typed (shared by every instrument). ``instrument_limits`` holds
    per-instrument-type sections generically: ``{instrument_type: {json_key:
    value}}``. Per-key constraints and default thresholds live in the model's
    instrument-type descriptors, not here — the config package stays a leaf and
    does not import the model.
    """

    common: CommonSoftLimits = field(default_factory=CommonSoftLimits)
    instrument_limits: dict[str, dict[str, float]] = field(default_factory=dict)

    def get_limit(self, section: str, key: str) -> float | None:
        """Return a config-supplied limit value, or None if not provided."""
        return self.instrument_limits.get(section, {}).get(key)


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
    Validate and parse the validation_limits configuration section.

    ``common`` is validated as a typed section. Every other section is parsed
    generically: each value must be numeric (per-key constraints and defaults
    live in the model's descriptors and are checked at startup, not here). The
    config package stays a leaf and does not import the model.

    Args:
        limits_dict: The validation_limits section from config
        errors: List to accumulate error messages

    Returns:
        ValidationLimits with parsed values or defaults
    """
    # Parse common limits (typed - shared by all instruments).
    common_dict = limits_dict.get("common", {})
    common_limits = _validate_common_limits(common_dict, errors)

    # Parse every other section generically.
    instrument_limits: dict[str, dict[str, float]] = {}
    for section, section_dict in limits_dict.items():
        if section == "common":
            continue
        prefix = f"validation_limits.{section}"
        if not isinstance(section_dict, dict):
            errors.append(f"{prefix} must be an object")
            continue
        parsed: dict[str, float] = {}
        for key, value in section_dict.items():
            if not isinstance(value, (int, float)):
                errors.append(
                    f"{prefix}.{key} must be numeric, got {type(value).__name__}"
                )
                continue
            parsed[key] = float(value)
        instrument_limits[section] = parsed

    return ValidationLimits(common=common_limits, instrument_limits=instrument_limits)


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
