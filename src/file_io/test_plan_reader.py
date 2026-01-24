"""Test plan CSV reader with support for multiple plan types."""

import csv
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
POWER_SUPPLY_COLUMNS = {"time", "voltage", "current"}
SIGNAL_GENERATOR_COLUMNS = {"time", "frequency", "power"}
OPTIONAL_COLUMNS = {"description", "type"}


def read_test_plan(file_path: str | Path) -> tuple[TestPlan | None, list[str]]:
    """
    Read a test plan from a CSV file.

    The plan type is determined by the 'type' column in the CSV.
    If no type column, defaults to power_supply for backwards compatibility.
    Step numbers are automatically calculated from row order (1-based).

    Power Supply CSV format:
        time,voltage,current,description
        0.0,5.0,1.0,Initial
        ...

    Signal Generator CSV format:
        type,time,frequency,power,description
        signal_generator,0.0,1000000,0,Start
        ...

    Args:
        file_path: Path to CSV file

    Returns:
        Tuple of (TestPlan/SignalGeneratorTestPlan or None, list of error messages)
    """
    errors: list[str] = []
    file_path = Path(file_path)

    # Check file exists
    if not file_path.exists():
        errors.append(f"File not found: {file_path}")
        return None, errors

    # Read CSV
    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                errors.append("CSV file is empty or has no header row")
                return None, errors

            # Normalize column names to lowercase
            columns = {name.lower().strip() for name in reader.fieldnames}
            column_map = {name.lower().strip(): name for name in reader.fieldnames}

            # Read all rows to determine type
            rows = list(reader)

            if not rows:
                errors.append("CSV file has no data rows")
                return None, errors

            # Determine plan type from first row's 'type' column, or infer from columns
            plan_type = _detect_plan_type(rows[0], column_map, columns)

            if plan_type is None:
                errors.append(
                    "Cannot determine plan type. Include 'type' column with "
                    f"'{PLAN_TYPE_POWER_SUPPLY}' or '{PLAN_TYPE_SIGNAL_GENERATOR}'"
                )
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
    except OSError as e:
        errors.append(f"Error reading file: {e}")
        return None, errors


def _detect_plan_type(
    first_row: dict[str, str],
    column_map: dict[str, str],
    columns: set[str],
) -> str | None:
    """
    Detect plan type from the first row or column structure.

    Args:
        first_row: First data row
        column_map: Mapping of normalized to actual column names
        columns: Set of normalized column names

    Returns:
        Plan type string or None if cannot determine
    """
    # Check for explicit type column
    if "type" in columns:
        actual_col = column_map.get("type")
        if actual_col:
            type_value = first_row.get(actual_col, "").strip().lower()
            if type_value in (PLAN_TYPE_POWER_SUPPLY, PLAN_TYPE_SIGNAL_GENERATOR):
                return type_value

    # Infer from columns (backwards compatibility)
    has_power_supply_cols = POWER_SUPPLY_COLUMNS.issubset(columns)
    has_signal_gen_cols = SIGNAL_GENERATOR_COLUMNS.issubset(columns)

    if has_power_supply_cols and not has_signal_gen_cols:
        return PLAN_TYPE_POWER_SUPPLY
    elif has_signal_gen_cols and not has_power_supply_cols:
        return PLAN_TYPE_SIGNAL_GENERATOR

    return None


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

    # Parse time
    time_str = _get_value(row, column_map, "time")
    try:
        time_seconds = float(time_str)
        if time_seconds < 0:
            errors.append(f"Row {row_num}: time must be >= 0, got {time_seconds}")
    except ValueError:
        errors.append(f"Row {row_num}: invalid time value '{time_str}'")
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
            time_seconds=time_seconds,
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

    # Parse time
    time_str = _get_value(row, column_map, "time")
    try:
        time_seconds = float(time_str)
        if time_seconds < 0:
            errors.append(f"Row {row_num}: time must be >= 0, got {time_seconds}")
    except ValueError:
        errors.append(f"Row {row_num}: invalid time value '{time_str}'")
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
            time_seconds=time_seconds,
            frequency=frequency,
            power=power,
            description=description,
        ),
        [],
    )
