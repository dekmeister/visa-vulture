"""Declarative field specs and table-column helpers for instrument types.

These drive generic CSV parsing, soft-limit validation, and plot-data extraction.
They are model-side (the view never imports them); the view-facing ``ColumnSpec``
type lives in the neutral ``view_specs`` leaf and is re-used here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...view_specs import ColumnSpec, ValueFormatter


@dataclass(frozen=True)
class SoftLimitSpec:
    """Soft (warning-only) limit configuration for a single step field.

    ``min_default``/``max_default`` are the fallback thresholds used when the
    config supplies no override. ``config_min`` is the constraint applied to a
    *config-supplied* limit value at startup (e.g. frequency limits must be
    ``>= 0``; power limits have no such constraint because dBm can be negative).
    """

    min_key: str | None = None  # JSON key, e.g. "power_min_dbm"
    max_key: str | None = None  # JSON key, e.g. "voltage_max_v"
    min_default: float | None = None
    max_default: float | None = None
    below_message: str = "below typical minimum"
    above_message: str = "exceeds typical equipment limits"
    config_min: float | None = None  # lower bound for config-supplied limit values
    config_min_exclusive: bool = False


@dataclass(frozen=True)
class StepFieldSpec:
    """Declarative description of one instrument-specific step field.

    Drives generic CSV parsing, soft-limit validation, and plot data extraction.
    """

    name: str  # step attribute AND CSV column ("voltage")
    unit: str  # "V", "Hz", "dBm"
    kind: Literal["float", "bool"] = "float"  # bool: modulation_enabled
    required: bool = True  # required CSV column?
    default: float | bool | None = None  # for optional columns
    hard_min: float | None = 0.0  # CSV hard-limit validation (error if below)
    hard_max: float | None = None  # CSV hard-limit validation (error if above)
    soft_limits: SoftLimitSpec | None = None
    axis: Literal["primary", "secondary"] | None = None  # plot preview extraction


# Shared column prefix and suffix. The common prefix (step / duration / abs_time)
# and the trailing description column are identical for every instrument type.
COMMON_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("step", "Step", 50, lambda s: str(s.step_number)),
    ColumnSpec("duration", "Duration (s)", 80, lambda s: f"{s.duration_seconds:.1f}"),
    ColumnSpec(
        "abs_time", "Abs. Time (s)", 80, lambda s: f"{s.absolute_time_seconds:.1f}"
    ),
)

_DESCRIPTION_COLUMN = ColumnSpec("description", "Description", 150, lambda s: s.description)


def make_columns(*specific: ColumnSpec) -> tuple[ColumnSpec, ...]:
    """Assemble a full column list: common prefix + specific + description."""
    return COMMON_COLUMNS + specific + (_DESCRIPTION_COLUMN,)


def default_columns(fields: tuple[StepFieldSpec, ...]) -> tuple[ColumnSpec, ...]:
    """Derive a full column list from field specs.

    Heading is ``"<Name> (<unit>)"`` with a ``{:.2f}`` float format (or
    ``"Enabled"``/``"Disabled"`` for bool fields). Built-in types override
    individual columns where today's formatting differs (SG engineering-units
    frequency, "Enabled"/"Disabled" modulation, power ``{:.1f}``); new types can
    use this directly where the defaults fit.
    """

    def _float_fn(name: str) -> ValueFormatter:
        return lambda s: f"{getattr(s, name):.2f}"

    def _bool_fn(name: str) -> ValueFormatter:
        return lambda s: "Enabled" if getattr(s, name) else "Disabled"

    specific: list[ColumnSpec] = []
    for spec in fields:
        heading = f"{spec.name.replace('_', ' ').title()} ({spec.unit})"
        value_fn = _bool_fn(spec.name) if spec.kind == "bool" else _float_fn(spec.name)
        specific.append(ColumnSpec(spec.name, heading, 80, value_fn))
    return make_columns(*specific)
