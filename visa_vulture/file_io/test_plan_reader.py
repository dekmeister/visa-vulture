"""Test plan CSV reader with support for multiple plan types.

CSV files use comment-line metadata at the top of the file to specify
the instrument type. The metadata format is:

    # instrument_type: power_supply

Followed by the standard CSV header and data rows.
"""

import csv
import io
import logging
from pathlib import Path

from ..model.test_plan import (
    TestPlan,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
)

logger = logging.getLogger(__name__)

# Column requirements by plan type
POWER_SUPPLY_COLUMNS = {"duration", "voltage", "current"}
SIGNAL_GENERATOR_COLUMNS = {"duration", "frequency", "power"}
OPTIONAL_COLUMNS = {"description"}

# Valid instrument types for metadata
_VALID_INSTRUMENT_TYPES = {PLAN_TYPE_POWER_SUPPLY, PLAN_TYPE_SIGNAL_GENERATOR}


def read_test_plan(file_path: str | Path) -> tuple[TestPlan | None, list[str]]:
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

    Returns:
        Tuple of (TestPlan or None, list of error messages)
    """
    errors: list[str] = []
    file_path = Path(file_path)

    # Check file exists
    if not file_path.exists():
        errors.append(f"File not found: {file_path}")
        return None, errors

    # Read file and parse metadata
    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            file_content = f.read()
    except OSError as e:
        errors.append(f"Error reading file: {e}")
        return None, errors

    metadata, csv_content = _parse_metadata(file_content)

    # Validate instrument_type metadata
    if not metadata:
        errors.append(
            "Missing required metadata. Add '# instrument_type: power_supply' "
            "or '# instrument_type: signal_generator' at the top of the CSV file"
        )
        return None, errors

    if "instrument_type" not in metadata:
        errors.append("Missing required metadata field 'instrument_type'")
        return None, errors

    plan_type = metadata["instrument_type"]
    if plan_type not in _VALID_INSTRUMENT_TYPES:
        errors.append(
            f"Invalid instrument_type '{plan_type}'. "
            f"Must be '{PLAN_TYPE_POWER_SUPPLY}' or '{PLAN_TYPE_SIGNAL_GENERATOR}'"
        )
        return None, errors

    # Parse CSV content
    try:
        reader = csv.DictReader(io.StringIO(csv_content))

        if reader.fieldnames is None:
            errors.append("CSV file is empty or has no header row")
            return None, errors

        # Normalize column names to lowercase
        columns = {name.lower().strip() for name in reader.fieldnames}
        column_map = {name.lower().strip(): name for name in reader.fieldnames}

        # Read all rows
        rows = list(reader)

        if not rows:
            errors.append("CSV file has no data rows")
            return None, errors

        # Validate columns for detected type
        if plan_type == PLAN_TYPE_POWER_SUPPLY:
            missing = POWER_SUPPLY_COLUMNS - columns
            if missing:
                errors.append(
                    f"Missing required columns for power supply: {', '.join(sorted(missing))}"
                )
                return None, errors
            return _parse_power_supply_plan(file_path, rows, column_map, errors)

        elif plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            missing = SIGNAL_GENERATOR_COLUMNS - columns
            if missing:
                errors.append(
                    f"Missing required columns for signal generator: {', '.join(sorted(missing))}"
                )
                return None, errors
            return _parse_signal_generator_plan(file_path, rows, column_map, errors)

        else:
            errors.append(f"Unknown plan type: '{plan_type}'")
            return None, errors

    except csv.Error as e:
        errors.append(f"CSV parsing error: {e}")
        return None, errors


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

    csv_content = "".join(lines[csv_start:])
    return metadata, csv_content


def _parse_power_supply_plan(
    file_path: Path,
    rows: list[dict[str, str]],
    column_map: dict[str, str],
    errors: list[str],
) -> tuple[TestPlan | None, list[str]]:
    """Parse rows into a power supply TestPlan."""
    steps: list[PowerSupplyTestStep] = []

    for row_num, row in enumerate(rows, start=2):
        step_number = row_num - 1  # 1-based step number (row 2 = step 1)
        step, row_errors = _parse_power_supply_row(
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
    test_plan = TestPlan(name=plan_name, steps=steps, plan_type=PLAN_TYPE_POWER_SUPPLY)

    validation_errors = test_plan.validate()
    if validation_errors:
        errors.extend(validation_errors)
        return None, errors

    logger.info(
        "Loaded power supply test plan '%s' from %s: %d steps",
        plan_name,
        file_path,
        len(steps),
    )
    return test_plan, []


def _parse_signal_generator_plan(
    file_path: Path,
    rows: list[dict[str, str]],
    column_map: dict[str, str],
    errors: list[str],
) -> tuple[TestPlan | None, list[str]]:
    """Parse rows into a signal generator TestPlan."""
    steps: list[SignalGeneratorTestStep] = []

    for row_num, row in enumerate(rows, start=2):
        step_number = row_num - 1  # 1-based step number (row 2 = step 1)
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
    test_plan = TestPlan(
        name=plan_name, steps=steps, plan_type=PLAN_TYPE_SIGNAL_GENERATOR
    )

    validation_errors = test_plan.validate()
    if validation_errors:
        errors.extend(validation_errors)
        return None, errors

    logger.info(
        "Loaded signal generator test plan '%s' from %s: %d steps",
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
    except ValueError:
        errors.append(f"Row {row_num}: invalid voltage value '{voltage_str}'")
        return None, errors

    # Parse current
    current_str = _get_value(row, column_map, "current")
    try:
        current = float(current_str)
        if current < 0:
            errors.append(f"Row {row_num}: current must be >= 0, got {current}")
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
    except ValueError:
        errors.append(f"Row {row_num}: invalid frequency value '{freq_str}'")
        return None, errors

    # Parse power (can be negative for dBm)
    power_str = _get_value(row, column_map, "power")
    try:
        power = float(power_str)
    except ValueError:
        errors.append(f"Row {row_num}: invalid power value '{power_str}'")
        return None, errors

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
            description=description,
        ),
        [],
    )
