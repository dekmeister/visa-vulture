"""Test plan CSV reader with support for multiple plan types.

CSV files use comment-line metadata at the top of the file to specify
the instrument type. The metadata format is:

    # instrument_type: power_supply

Followed by the standard CSV header and data rows.
"""

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

from typing import Union

from ..config.schema import ValidationLimits
from ..model.test_plan import (
    TestPlan,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    ModulationType,
    ModulationConfig,
    AMModulationConfig,
    FMModulationConfig,
    HARD_LIMIT_POWER_MIN_DBM,
    HARD_LIMIT_POWER_MAX_DBM,
    HARD_LIMIT_FREQUENCY_MAX_HZ,
    HARD_LIMIT_VOLTAGE_MAX_V,
    HARD_LIMIT_CURRENT_MAX_A,
)


@dataclass
class TestPlanResult:
    """Result of reading a test plan with errors and warnings.

    Attributes:
        plan: The parsed TestPlan, or None if errors occurred
        errors: List of error messages that prevented loading
        warnings: List of warning messages (soft limit violations)
    """

    plan: TestPlan | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

logger = logging.getLogger(__name__)

# Column requirements by plan type
POWER_SUPPLY_COLUMNS = {"duration", "voltage", "current"}
SIGNAL_GENERATOR_COLUMNS = {"duration", "frequency", "power"}
OPTIONAL_COLUMNS = {"description"}

# Valid instrument types for metadata
_VALID_INSTRUMENT_TYPES = {PLAN_TYPE_POWER_SUPPLY, PLAN_TYPE_SIGNAL_GENERATOR}

# Modulation metadata keys
MODULATION_TYPE_KEY = "modulation_type"
MODULATION_FREQUENCY_KEY = "modulation_frequency"
AM_DEPTH_KEY = "am_depth"
FM_DEVIATION_KEY = "fm_deviation"

# Valid modulation type values
VALID_MODULATION_TYPES = {"am", "fm"}


def read_test_plan(
    file_path: str | Path,
    soft_limits: ValidationLimits | None = None,
) -> TestPlanResult:
    """
    Read a test plan from a CSV file.

    The plan type is determined by required '# instrument_type' metadata
    at the top of the CSV file. Step numbers are automatically calculated
    from row order (1-based).

    Power Supply CSV format:
        # instrument_type: power_supply
        duration,voltage,current,description
        5.0,5.0,1.0,Initial
        ...

    Signal Generator CSV format:
        # instrument_type: signal_generator
        duration,frequency,power,description
        5.0,1000000,0,Start
        ...

    Args:
        file_path: Path to CSV file
        soft_limits: Optional ValidationLimits for soft limit checking.
            If provided, values exceeding soft limits generate warnings.
            If None, soft limit validation is skipped.

    Returns:
        TestPlanResult with plan (or None if errors), errors list, and warnings list
    """
    errors: list[str] = []
    file_path = Path(file_path)

    # Check file exists
    if not file_path.exists():
        errors.append(f"File not found: {file_path}")
        return TestPlanResult(plan=None, errors=errors)

    # Read file and parse metadata
    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            file_content = f.read()
    except OSError as e:
        errors.append(f"Error reading file: {e}")
        return TestPlanResult(plan=None, errors=errors)

    metadata, csv_content = _parse_metadata(file_content)

    # Validate instrument_type metadata
    if not metadata:
        errors.append(
            "Missing required metadata. Add '# instrument_type: power_supply' "
            "or '# instrument_type: signal_generator' at the top of the CSV file"
        )
        return TestPlanResult(plan=None, errors=errors)

    if "instrument_type" not in metadata:
        errors.append("Missing required metadata field 'instrument_type'")
        return TestPlanResult(plan=None, errors=errors)

    plan_type = metadata["instrument_type"]
    if plan_type not in _VALID_INSTRUMENT_TYPES:
        errors.append(
            f"Invalid instrument_type '{plan_type}'. "
            f"Must be '{PLAN_TYPE_POWER_SUPPLY}' or '{PLAN_TYPE_SIGNAL_GENERATOR}'"
        )
        return TestPlanResult(plan=None, errors=errors)

    # Parse CSV content
    try:
        reader = csv.DictReader(io.StringIO(csv_content))

        if reader.fieldnames is None:
            errors.append("CSV file is empty or has no header row")
            return TestPlanResult(plan=None, errors=errors)

        # Normalize column names to lowercase
        columns = {name.lower().strip() for name in reader.fieldnames}
        column_map = {name.lower().strip(): name for name in reader.fieldnames}

        # Read all rows
        rows = list(reader)

        if not rows:
            errors.append("CSV file has no data rows")
            return TestPlanResult(plan=None, errors=errors)

        # Validate columns for detected type
        if plan_type == PLAN_TYPE_POWER_SUPPLY:
            missing = POWER_SUPPLY_COLUMNS - columns
            if missing:
                errors.append(
                    f"Missing required columns for power supply: {', '.join(sorted(missing))}"
                )
                return TestPlanResult(plan=None, errors=errors)
            plan, parse_errors = _parse_test_plan(
                file_path, rows, column_map, errors, plan_type
            )
            if parse_errors:
                return TestPlanResult(plan=None, errors=parse_errors)
            warnings = (
                _validate_soft_limits(plan, soft_limits)
                if plan and soft_limits
                else []
            )
            return TestPlanResult(plan=plan, errors=[], warnings=warnings)

        elif plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            missing = SIGNAL_GENERATOR_COLUMNS - columns
            if missing:
                errors.append(
                    f"Missing required columns for signal generator: {', '.join(sorted(missing))}"
                )
                return TestPlanResult(plan=None, errors=errors)

            # Parse modulation config from metadata (may be None if not specified)
            modulation_config = _parse_modulation_config(metadata, errors)
            if errors:
                return TestPlanResult(plan=None, errors=errors)

            result, parse_errors = _parse_test_plan(
                file_path, rows, column_map, errors, plan_type
            )

            if parse_errors:
                return TestPlanResult(plan=None, errors=parse_errors)

            # Attach modulation config to the test plan if present
            if result is not None and modulation_config is not None:
                result = TestPlan(
                    name=result.name,
                    plan_type=result.plan_type,
                    steps=result.steps,
                    description=result.description,
                    modulation_config=modulation_config,
                )

            warnings = (
                _validate_soft_limits(result, soft_limits)
                if result and soft_limits
                else []
            )
            return TestPlanResult(plan=result, errors=[], warnings=warnings)

        else:
            errors.append(f"Unknown plan type: '{plan_type}'")
            return TestPlanResult(plan=None, errors=errors)

    except csv.Error as e:
        errors.append(f"CSV parsing error: {e}")
        return TestPlanResult(plan=None, errors=errors)


def _parse_metadata(file_content: str) -> tuple[dict[str, str], str]:
    """
    Parse comment-line metadata from the top of a CSV file.

    Metadata lines start with '#' and use 'key: value' format.
    Returns the metadata dict and the remaining CSV content.

    Args:
        file_content: Full file content as string

    Returns:
        Tuple of (metadata dict, remaining CSV content)
    """
    metadata: dict[str, str] = {}
    lines = file_content.splitlines(keepends=True)
    csv_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            # Remove the '#' prefix and parse key: value
            comment_body = stripped[1:].strip()
            if ":" in comment_body:
                key, _, value = comment_body.partition(":")
                metadata[key.strip().lower()] = value.strip().lower()
            csv_start = i + 1
        else:
            break

    logger.debug("Loaded metadata from testplan file: %s", metadata)

    csv_content = "".join(lines[csv_start:])
    return metadata, csv_content


def _parse_test_plan(
    file_path: Path,
    rows: list[dict[str, str]],
    column_map: dict[str, str],
    errors: list[str],
    plan_type: str,
) -> tuple[TestPlan | None, list[str]]:
    """Parse rows into a suitable type of TestPlan."""
    if plan_type not in (PLAN_TYPE_POWER_SUPPLY, PLAN_TYPE_SIGNAL_GENERATOR):
        errors.append(f"Unknown plan type: '{plan_type}'")
        return None, errors

    steps: list[PowerSupplyTestStep | SignalGeneratorTestStep] = []

    for row_num, row in enumerate(rows, start=2):
        step_number = row_num - 1  # 1-based step number (row 2 = step 1)
        step: PowerSupplyTestStep | SignalGeneratorTestStep | None = None
        row_errors: list[str] = []
        if plan_type == PLAN_TYPE_POWER_SUPPLY:
            step, row_errors = _parse_power_supply_row(
                row, column_map, row_num, step_number
            )
        elif plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            step, row_errors = _parse_signal_generator_row(
                row, column_map, row_num, step_number
            )
        if row_errors:
            errors.extend(row_errors)
        elif step is not None:
            steps.append(step)

    if errors:
        return None, errors

    if not steps:
        errors.append("No valid steps found in CSV")
        return None, errors

    plan_name = file_path.stem
    test_plan = TestPlan(name=plan_name, steps=steps, plan_type=plan_type)

    validation_errors = test_plan.validate()
    if validation_errors:
        errors.extend(validation_errors)
        return None, errors

    logger.info(
        "Loaded %s test plan '%s' from %s: %d steps",
        plan_type,
        plan_name,
        file_path,
        len(steps),
    )
    return test_plan, []


def _get_value(
    row: dict[str, str], column_map: dict[str, str], normalized_name: str
) -> str:
    """Get value from row using column mapping."""
    actual_name = column_map.get(normalized_name)
    if actual_name is None:
        return ""
    return row.get(actual_name, "").strip()


def _parse_power_supply_row(
    row: dict[str, str],
    column_map: dict[str, str],
    row_num: int,
    step_number: int,
) -> tuple[PowerSupplyTestStep | None, list[str]]:
    """Parse a single CSV row into a power supply TestStep."""
    errors: list[str] = []

    # Parse duration
    duration_str = _get_value(row, column_map, "duration")
    try:
        duration_seconds = float(duration_str)
        if duration_seconds < 0:
            errors.append(
                f"Row {row_num}: duration must be >= 0, got {duration_seconds}"
            )
    except ValueError:
        errors.append(f"Row {row_num}: invalid duration value '{duration_str}'")
        return None, errors

    # Parse voltage
    voltage_str = _get_value(row, column_map, "voltage")
    try:
        voltage = float(voltage_str)
        if voltage < 0:
            errors.append(f"Row {row_num}: voltage must be >= 0, got {voltage}")
        elif voltage > HARD_LIMIT_VOLTAGE_MAX_V:
            errors.append(
                f"Row {row_num}: voltage {voltage} V exceeds maximum "
                f"({HARD_LIMIT_VOLTAGE_MAX_V} V)"
            )
    except ValueError:
        errors.append(f"Row {row_num}: invalid voltage value '{voltage_str}'")
        return None, errors

    # Parse current
    current_str = _get_value(row, column_map, "current")
    try:
        current = float(current_str)
        if current < 0:
            errors.append(f"Row {row_num}: current must be >= 0, got {current}")
        elif current > HARD_LIMIT_CURRENT_MAX_A:
            errors.append(
                f"Row {row_num}: current {current} A exceeds maximum "
                f"({HARD_LIMIT_CURRENT_MAX_A} A)"
            )
    except ValueError:
        errors.append(f"Row {row_num}: invalid current value '{current_str}'")
        return None, errors

    # Parse optional description
    description = _get_value(row, column_map, "description")

    if errors:
        return None, errors

    return (
        PowerSupplyTestStep(
            step_number=step_number,
            duration_seconds=duration_seconds,
            voltage=voltage,
            current=current,
            description=description,
        ),
        [],
    )


def _parse_signal_generator_row(
    row: dict[str, str],
    column_map: dict[str, str],
    row_num: int,
    step_number: int,
) -> tuple[SignalGeneratorTestStep | None, list[str]]:
    """Parse a single CSV row into a signal generator TestStep."""
    errors: list[str] = []

    # Parse duration
    duration_str = _get_value(row, column_map, "duration")
    try:
        duration_seconds = float(duration_str)
        if duration_seconds < 0:
            errors.append(
                f"Row {row_num}: duration must be >= 0, got {duration_seconds}"
            )
    except ValueError:
        errors.append(f"Row {row_num}: invalid duration value '{duration_str}'")
        return None, errors

    # Parse frequency
    freq_str = _get_value(row, column_map, "frequency")
    try:
        frequency = float(freq_str)
        if frequency < 0:
            errors.append(f"Row {row_num}: frequency must be >= 0, got {frequency}")
        elif frequency > HARD_LIMIT_FREQUENCY_MAX_HZ:
            errors.append(
                f"Row {row_num}: frequency {frequency} Hz exceeds maximum "
                f"({HARD_LIMIT_FREQUENCY_MAX_HZ} Hz)"
            )
    except ValueError:
        errors.append(f"Row {row_num}: invalid frequency value '{freq_str}'")
        return None, errors

    # Parse power (can be negative for dBm, but within reasonable limits)
    power_str = _get_value(row, column_map, "power")
    try:
        power = float(power_str)
        if power < HARD_LIMIT_POWER_MIN_DBM:
            errors.append(
                f"Row {row_num}: power {power} dBm below minimum "
                f"({HARD_LIMIT_POWER_MIN_DBM} dBm)"
            )
        elif power > HARD_LIMIT_POWER_MAX_DBM:
            errors.append(
                f"Row {row_num}: power {power} dBm exceeds maximum "
                f"({HARD_LIMIT_POWER_MAX_DBM} dBm)"
            )
    except ValueError:
        errors.append(f"Row {row_num}: invalid power value '{power_str}'")
        return None, errors

    # Parse optional modulation_enabled
    modulation_enabled = False
    mod_enabled_str = _get_value(row, column_map, "modulation_enabled")
    if mod_enabled_str:
        mod_enabled_lower = mod_enabled_str.lower()
        if mod_enabled_lower in ("true", "1", "yes"):
            modulation_enabled = True
        elif mod_enabled_lower in ("false", "0", "no", ""):
            modulation_enabled = False
        else:
            errors.append(
                f"Row {row_num}: invalid modulation_enabled value '{mod_enabled_str}'. "
                f"Use true/false, 1/0, or yes/no"
            )

    # Parse optional description
    description = _get_value(row, column_map, "description")

    if errors:
        return None, errors

    return (
        SignalGeneratorTestStep(
            step_number=step_number,
            duration_seconds=duration_seconds,
            frequency=frequency,
            power=power,
            modulation_enabled=modulation_enabled,
            description=description,
        ),
        [],
    )


def _parse_modulation_config(
    metadata: dict[str, str],
    errors: list[str],
) -> ModulationConfig | None:
    """
    Parse modulation configuration from metadata.

    Returns None if no modulation type specified.
    Appends to errors list if modulation type is specified but
    required parameters are missing or invalid.

    Args:
        metadata: Parsed metadata dictionary
        errors: List to accumulate error messages

    Returns:
        ModulationConfig or None if no modulation configured
    """
    mod_type_str = metadata.get(MODULATION_TYPE_KEY)
    if not mod_type_str:
        return None

    if mod_type_str not in VALID_MODULATION_TYPES:
        errors.append(
            f"Invalid modulation_type '{mod_type_str}'. "
            f"Must be one of: {', '.join(sorted(VALID_MODULATION_TYPES))}"
        )
        return None

    # Parse common modulation_frequency
    mod_freq_str = metadata.get(MODULATION_FREQUENCY_KEY)
    if not mod_freq_str:
        errors.append(
            f"Missing required metadata '{MODULATION_FREQUENCY_KEY}' "
            f"when modulation_type is '{mod_type_str}'"
        )
        return None

    try:
        mod_freq = float(mod_freq_str)
        if mod_freq <= 0:
            errors.append(f"modulation_frequency must be > 0, got {mod_freq}")
            return None
    except ValueError:
        errors.append(f"Invalid modulation_frequency value '{mod_freq_str}'")
        return None

    # Parse type-specific parameters
    if mod_type_str == "am":
        return _parse_am_config(metadata, mod_freq, errors)
    elif mod_type_str == "fm":
        return _parse_fm_config(metadata, mod_freq, errors)

    return None


def _parse_am_config(
    metadata: dict[str, str],
    mod_freq: float,
    errors: list[str],
) -> AMModulationConfig | None:
    """Parse AM-specific configuration from metadata."""
    depth_str = metadata.get(AM_DEPTH_KEY)
    if not depth_str:
        errors.append(f"Missing required metadata '{AM_DEPTH_KEY}' for AM modulation")
        return None

    try:
        depth = float(depth_str)
        if not 0 <= depth <= 100:
            errors.append(f"am_depth must be 0-100%, got {depth}")
            return None
    except ValueError:
        errors.append(f"Invalid am_depth value '{depth_str}'")
        return None

    return AMModulationConfig(
        modulation_type=ModulationType.AM,
        modulation_frequency=mod_freq,
        depth=depth,
    )


def _parse_fm_config(
    metadata: dict[str, str],
    mod_freq: float,
    errors: list[str],
) -> FMModulationConfig | None:
    """Parse FM-specific configuration from metadata."""
    deviation_str = metadata.get(FM_DEVIATION_KEY)
    if not deviation_str:
        errors.append(
            f"Missing required metadata '{FM_DEVIATION_KEY}' for FM modulation"
        )
        return None

    try:
        deviation = float(deviation_str)
        if deviation <= 0:
            errors.append(f"fm_deviation must be > 0, got {deviation}")
            return None
    except ValueError:
        errors.append(f"Invalid fm_deviation value '{deviation_str}'")
        return None

    return FMModulationConfig(
        modulation_type=ModulationType.FM,
        modulation_frequency=mod_freq,
        deviation=deviation,
    )


def _check_soft_limit(
    warnings: list[str],
    step_number: int,
    field: str,
    value: float,
    limit: float,
    unit: str,
    description: str,
    direction: str = "exceeds",
) -> None:
    """Append a soft-limit warning and log it."""
    warnings.append(
        f"Step {step_number}: {field} {value} {unit} "
        f"{description} ({limit} {unit})"
    )
    logger.warning(
        "Step %d: %s %.1f %s %s soft limit of %.1f %s",
        step_number, field, value, unit, direction, limit, unit,
    )


def _validate_soft_limits(
    plan: TestPlan,
    limits: ValidationLimits,
) -> list[str]:
    """
    Check test plan against soft limits.

    Soft limits generate warnings but do not prevent loading.
    Values outside soft limits may indicate user error but are
    not physically impossible.

    Args:
        plan: The parsed test plan to validate
        limits: ValidationLimits containing soft limit thresholds

    Returns:
        List of warning messages (empty if all within limits)
    """
    warnings: list[str] = []

    for step in plan.steps:
        if step.duration_seconds > limits.common.duration_max_s:
            _check_soft_limit(
                warnings, step.step_number, "duration",
                step.duration_seconds, limits.common.duration_max_s,
                "s", "exceeds typical maximum",
            )

        if isinstance(step, SignalGeneratorTestStep):
            if step.power < limits.signal_generator.power_min_dbm:
                _check_soft_limit(
                    warnings, step.step_number, "power",
                    step.power, limits.signal_generator.power_min_dbm,
                    "dBm", "below typical noise floor", "below",
                )
            if step.power > limits.signal_generator.power_max_dbm:
                _check_soft_limit(
                    warnings, step.step_number, "power",
                    step.power, limits.signal_generator.power_max_dbm,
                    "dBm", "exceeds typical equipment limits",
                )
            if step.frequency < limits.signal_generator.frequency_min_hz:
                _check_soft_limit(
                    warnings, step.step_number, "frequency",
                    step.frequency, limits.signal_generator.frequency_min_hz,
                    "Hz", "below typical minimum", "below",
                )
            if step.frequency > limits.signal_generator.frequency_max_hz:
                _check_soft_limit(
                    warnings, step.step_number, "frequency",
                    step.frequency, limits.signal_generator.frequency_max_hz,
                    "Hz", "exceeds typical equipment limits",
                )

        elif isinstance(step, PowerSupplyTestStep):
            if step.voltage > limits.power_supply.voltage_max_v:
                _check_soft_limit(
                    warnings, step.step_number, "voltage",
                    step.voltage, limits.power_supply.voltage_max_v,
                    "V", "exceeds typical lab supply limits",
                )
            if step.current > limits.power_supply.current_max_a:
                _check_soft_limit(
                    warnings, step.step_number, "current",
                    step.current, limits.power_supply.current_max_a,
                    "A", "exceeds typical lab supply limits",
                )

    return warnings
