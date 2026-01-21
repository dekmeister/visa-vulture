"""Test plan CSV reader."""

import csv
import logging
from pathlib import Path

from ..model.test_plan import TestPlan, TestStep

logger = logging.getLogger(__name__)

# Expected column names (case-insensitive)
REQUIRED_COLUMNS = {"step", "time", "voltage", "current"}
OPTIONAL_COLUMNS = {"description"}


def read_test_plan(file_path: str | Path) -> tuple[TestPlan | None, list[str]]:
    """
    Read a test plan from a CSV file.

    Expected CSV format:
        step,time,voltage,current,description
        1,0.0,5.0,1.0,Initial
        2,10.0,10.0,2.0,Ramp up
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

    # Read CSV
    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                errors.append("CSV file is empty or has no header row")
                return None, errors

            # Normalize column names to lowercase
            columns = {name.lower().strip() for name in reader.fieldnames}

            # Check required columns
            missing = REQUIRED_COLUMNS - columns
            if missing:
                errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
                return None, errors

            # Map actual column names to normalized names
            column_map = {name.lower().strip(): name for name in reader.fieldnames}

            # Parse rows
            steps: list[TestStep] = []
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                step, row_errors = _parse_row(row, column_map, row_num)
                if row_errors:
                    errors.extend(row_errors)
                elif step is not None:
                    steps.append(step)

    except csv.Error as e:
        errors.append(f"CSV parsing error: {e}")
        return None, errors
    except OSError as e:
        errors.append(f"Error reading file: {e}")
        return None, errors

    if errors:
        return None, errors

    if not steps:
        errors.append("No valid steps found in CSV")
        return None, errors

    # Create test plan
    plan_name = file_path.stem
    test_plan = TestPlan(name=plan_name, steps=steps)

    # Validate the plan
    validation_errors = test_plan.validate()
    if validation_errors:
        errors.extend(validation_errors)
        return None, errors

    logger.info("Loaded test plan '%s' from %s: %d steps", plan_name, file_path, len(steps))
    return test_plan, []


def _parse_row(
    row: dict[str, str],
    column_map: dict[str, str],
    row_num: int,
) -> tuple[TestStep | None, list[str]]:
    """
    Parse a single CSV row into a TestStep.

    Args:
        row: CSV row as dictionary
        column_map: Mapping of normalized to actual column names
        row_num: Row number for error messages

    Returns:
        Tuple of (TestStep or None, list of error messages)
    """
    errors: list[str] = []

    def get_value(normalized_name: str) -> str:
        """Get value from row using column mapping."""
        actual_name = column_map.get(normalized_name)
        if actual_name is None:
            return ""
        return row.get(actual_name, "").strip()

    # Parse step number
    step_str = get_value("step")
    try:
        step_number = int(step_str)
        if step_number < 1:
            errors.append(f"Row {row_num}: step must be >= 1, got {step_number}")
    except ValueError:
        errors.append(f"Row {row_num}: invalid step number '{step_str}'")
        return None, errors

    # Parse time
    time_str = get_value("time")
    try:
        time_seconds = float(time_str)
        if time_seconds < 0:
            errors.append(f"Row {row_num}: time must be >= 0, got {time_seconds}")
    except ValueError:
        errors.append(f"Row {row_num}: invalid time value '{time_str}'")
        return None, errors

    # Parse voltage
    voltage_str = get_value("voltage")
    try:
        voltage = float(voltage_str)
        if voltage < 0:
            errors.append(f"Row {row_num}: voltage must be >= 0, got {voltage}")
    except ValueError:
        errors.append(f"Row {row_num}: invalid voltage value '{voltage_str}'")
        return None, errors

    # Parse current
    current_str = get_value("current")
    try:
        current = float(current_str)
        if current < 0:
            errors.append(f"Row {row_num}: current must be >= 0, got {current}")
    except ValueError:
        errors.append(f"Row {row_num}: invalid current value '{current_str}'")
        return None, errors

    # Parse optional description
    description = get_value("description")

    if errors:
        return None, errors

    return (
        TestStep(
            step_number=step_number,
            time_seconds=time_seconds,
            voltage=voltage,
            current=current,
            description=description,
        ),
        [],
    )
