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

from typing import Any

from ..config.schema import ValidationLimits
from ..instrument_specs import StepFieldSpec
from ..model.instrument_types import INSTRUMENT_TYPE_REGISTRY, InstrumentTypeDescriptor
from ..model.test_plan import TestPlan, TestStep


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

# Valid instrument types and their required CSV columns are derived from the
# instrument-type registry: required columns are "duration" plus every required
# field spec. Adding a new instrument type needs no edit here.
_VALID_INSTRUMENT_TYPES = set(INSTRUMENT_TYPE_REGISTRY)

_COLUMN_REQUIREMENTS: dict[str, set[str]] = {
    instrument_type: {"duration"}
    | {spec.name for spec in descriptor.fields if spec.required}
    for instrument_type, descriptor in INSTRUMENT_TYPE_REGISTRY.items()
}


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
    file_path = Path(file_path)

    if not file_path.exists():
        return TestPlanResult(plan=None, errors=[f"File not found: {file_path}"])

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            file_content = f.read()
    except OSError as e:
        return TestPlanResult(plan=None, errors=[f"Error reading file: {e}"])

    metadata, csv_content = _parse_metadata(file_content)

    if not metadata:
        return TestPlanResult(
            plan=None,
            errors=[
                "Missing required metadata. Add '# instrument_type: power_supply' "
                "or '# instrument_type: signal_generator' at the top of the CSV file"
            ],
        )

    if "instrument_type" not in metadata:
        return TestPlanResult(
            plan=None,
            errors=["Missing required metadata field 'instrument_type'"],
        )

    instrument_type = metadata["instrument_type"]
    if instrument_type not in _VALID_INSTRUMENT_TYPES:
        valid = ", ".join(f"'{t}'" for t in sorted(_VALID_INSTRUMENT_TYPES))
        return TestPlanResult(
            plan=None,
            errors=[
                f"Invalid instrument_type '{instrument_type}'. Must be one of: {valid}"
            ],
        )

    try:
        return _parse_csv_content(
            csv_content, metadata, file_path, instrument_type, soft_limits
        )
    except csv.Error as e:
        return TestPlanResult(plan=None, errors=[f"CSV parsing error: {e}"])


def _parse_csv_content(
    csv_content: str,
    metadata: dict[str, str],
    file_path: Path,
    instrument_type: str,
    soft_limits: ValidationLimits | None,
) -> TestPlanResult:
    """Parse CSV content into a TestPlanResult."""
    errors: list[str] = []

    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        return TestPlanResult(
            plan=None, errors=["CSV file is empty or has no header row"]
        )

    columns = {name.lower().strip() for name in reader.fieldnames}
    column_map = {name.lower().strip(): name for name in reader.fieldnames}

    rows = list(reader)
    if not rows:
        return TestPlanResult(plan=None, errors=["CSV file has no data rows"])

    descriptor = INSTRUMENT_TYPE_REGISTRY[instrument_type]

    # Validate required columns
    required = _COLUMN_REQUIREMENTS[instrument_type]
    missing = required - columns
    if missing:
        return TestPlanResult(
            plan=None,
            errors=[
                f"Missing required columns for {instrument_type.replace('_', ' ')}: "
                f"{', '.join(sorted(missing))}"
            ],
        )

    # Parse plan-level metadata (e.g. signal generator modulation) via the
    # descriptor hook. Returns extra TestPlan kwargs.
    plan_kwargs: dict[str, Any] = {}
    if descriptor.parse_plan_metadata is not None:
        plan_kwargs = descriptor.parse_plan_metadata(metadata, errors)
        if errors:
            return TestPlanResult(plan=None, errors=errors)

    # Parse rows into steps
    plan, parse_errors = _parse_test_plan(
        file_path, rows, column_map, errors, descriptor, plan_kwargs
    )
    if parse_errors:
        return TestPlanResult(plan=None, errors=parse_errors)

    # Validate soft limits
    warnings = _validate_soft_limits(plan, soft_limits) if plan and soft_limits else []
    return TestPlanResult(plan=plan, errors=[], warnings=warnings)


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
    descriptor: InstrumentTypeDescriptor,
    plan_kwargs: dict[str, Any],
) -> tuple[TestPlan | None, list[str]]:
    """Parse rows into a TestPlan using the instrument-type descriptor."""
    instrument_type = descriptor.instrument_type
    steps: list[TestStep] = []

    for row_num, row in enumerate(rows, start=2):
        step_number = row_num - 1  # 1-based step number (row 2 = step 1)
        step, row_errors = _parse_row(
            row, column_map, row_num, step_number, descriptor
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
        name=plan_name,
        steps=steps,
        instrument_type=instrument_type,
        **plan_kwargs,
    )

    validation_errors = test_plan.validate()
    if validation_errors:
        errors.extend(validation_errors)
        return None, errors

    logger.info(
        "Loaded %s test plan '%s' from %s: %d steps",
        instrument_type,
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


def _parse_float_field(
    row: dict[str, str],
    column_map: dict[str, str],
    field_name: str,
    row_num: int,
    errors: list[str],
    *,
    min_value: float | None = 0.0,
    max_value: float | None = None,
    unit: str = "",
) -> float | None:
    """Parse and validate a float field from a CSV row.

    Returns the parsed value, or None if the value couldn't be parsed.
    Range violations are appended to errors but the value is still returned.
    """
    raw = _get_value(row, column_map, field_name)
    try:
        value = float(raw)
    except ValueError:
        errors.append(f"Row {row_num}: invalid {field_name} value '{raw}'")
        return None

    if min_value is not None and value < min_value:
        if min_value == 0:
            errors.append(f"Row {row_num}: {field_name} must be >= 0, got {value}")
        else:
            unit_str = f" {unit}" if unit else ""
            errors.append(
                f"Row {row_num}: {field_name} {value}{unit_str} below minimum "
                f"({min_value}{unit_str})"
            )
    elif max_value is not None and value > max_value:
        unit_str = f" {unit}" if unit else ""
        errors.append(
            f"Row {row_num}: {field_name} {value}{unit_str} exceeds maximum "
            f"({max_value}{unit_str})"
        )

    return value


def _parse_bool_field(
    row: dict[str, str],
    column_map: dict[str, str],
    spec: StepFieldSpec,
    row_num: int,
    errors: list[str],
) -> bool:
    """Parse an optional boolean field (e.g. modulation_enabled) from a row."""
    default = bool(spec.default) if spec.default is not None else False
    raw = _get_value(row, column_map, spec.name)
    if not raw:
        return default

    lowered = raw.lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no", ""):
        return False

    errors.append(
        f"Row {row_num}: invalid {spec.name} value '{raw}'. "
        f"Use true/false, 1/0, or yes/no"
    )
    return default


def _parse_row(
    row: dict[str, str],
    column_map: dict[str, str],
    row_num: int,
    step_number: int,
    descriptor: InstrumentTypeDescriptor,
) -> tuple[TestStep | None, list[str]]:
    """Parse a single CSV row into the descriptor's step dataclass.

    Iterates the descriptor's field specs: float fields use the shared range
    parser (hard min/max + unit from the spec), bool fields use _parse_bool_field.
    An unparseable numeric value short-circuits the row; range/format violations
    accumulate and fail the row at the end (preserving prior behaviour).
    """
    errors: list[str] = []

    duration_seconds = _parse_float_field(row, column_map, "duration", row_num, errors)
    if duration_seconds is None:
        return None, errors

    field_values: dict[str, float | bool] = {}
    for spec in descriptor.fields:
        if spec.kind == "bool":
            field_values[spec.name] = _parse_bool_field(
                row, column_map, spec, row_num, errors
            )
        else:
            value = _parse_float_field(
                row,
                column_map,
                spec.name,
                row_num,
                errors,
                min_value=spec.hard_min,
                max_value=spec.hard_max,
                unit=spec.unit,
            )
            if value is None:
                return None, errors
            field_values[spec.name] = value

    description = _get_value(row, column_map, "description")

    if errors:
        return None, errors

    step = descriptor.step_cls(
        step_number=step_number,
        duration_seconds=duration_seconds,
        description=description,
        **field_values,
    )
    return step, []


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
        f"Step {step_number}: {field} {value} {unit} " f"{description} ({limit} {unit})"
    )
    logger.warning(
        "Step %d: %s %.1f %s %s soft limit of %.1f %s",
        step_number,
        field,
        value,
        unit,
        direction,
        limit,
        unit,
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

    descriptor = INSTRUMENT_TYPE_REGISTRY.get(plan.instrument_type)

    for step in plan.steps:
        if step.duration_seconds > limits.common.duration_max_s:
            _check_soft_limit(
                warnings,
                step.step_number,
                "duration",
                step.duration_seconds,
                limits.common.duration_max_s,
                "s",
                "exceeds typical maximum",
            )

        if descriptor is None:
            continue

        for spec in descriptor.fields:
            soft = spec.soft_limits
            if soft is None:
                continue
            value = getattr(step, spec.name)

            if soft.min_key is not None:
                minimum = limits.get_limit(plan.instrument_type, soft.min_key)
                if minimum is None:
                    minimum = soft.min_default
                if minimum is not None and value < minimum:
                    _check_soft_limit(
                        warnings,
                        step.step_number,
                        spec.name,
                        value,
                        minimum,
                        spec.unit,
                        soft.below_message,
                        "below",
                    )

            if soft.max_key is not None:
                maximum = limits.get_limit(plan.instrument_type, soft.max_key)
                if maximum is None:
                    maximum = soft.max_default
                if maximum is not None and value > maximum:
                    _check_soft_limit(
                        warnings,
                        step.step_number,
                        spec.name,
                        value,
                        maximum,
                        spec.unit,
                        soft.above_message,
                    )

    return warnings
