"""Pure-data presentation types for instrument types, consumed by the view.

This is a neutral leaf module: it imports from neither ``model`` nor ``view``
(standard library + ``typing`` only). Both the model and the view may import it.

The model owns the instrument-type registry and embeds these specs in each
descriptor; ``main.py`` derives ``{instrument_type: descriptor.view}`` and injects
it into the view. Keeping the spec *types* here lets the view consume presentation
data without importing the model, preserving the MVP dependency direction.

Parsing-side specs (``StepFieldSpec``/``SoftLimitSpec``) and column helpers live
in ``model/instrument_types/fields.py`` — the view never uses them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

# Type aliases — full signatures so mypy checks descriptor definitions.
ValueFormatter = Callable[[Any], str]  # step -> table cell text
StatusFormatter = Callable[[Any, int, int], str]  # (step, current, total) -> status text
StepDetailsFormatter = Callable[[Any], str]  # step -> Start-from dialog text


@dataclass(frozen=True)
class ColumnSpec:
    """A single column in the test-points table."""

    column_id: str
    heading: str  # "Voltage (V)"
    width: int
    value_fn: ValueFormatter  # formats a step attr; duck-typed, no model import


@dataclass(frozen=True)
class AxisConfig:
    """Configuration for a single Y-axis on a plot panel.

    Attributes:
        label: Axis label including units, e.g. "Voltage (V)"
        color: Matplotlib color string for axis label, ticks, and line
        legend_label: Text shown in the plot legend, e.g. "Voltage"
        default_scale: Initial Y-axis scale, either "linear" or "log"
        default_ylim: Y-axis limits used when clearing the plot, as (min, max)
        lower_bound_zero: Whether the lower Y bound should be clamped to 0
            in linear mode when auto-scaling
        linear_only: Whether the axis is restricted to linear scale
    """

    label: str
    color: str
    legend_label: str
    default_scale: str = "linear"
    default_ylim: tuple[float, float] = (0.0, 1.0)
    lower_bound_zero: bool = True
    linear_only: bool = False


@dataclass(frozen=True)
class InstrumentViewSpec:
    """Pure-data presentation spec for one instrument type (no Tkinter)."""

    tab_label: str  # "Power Supply"
    columns: tuple[ColumnSpec, ...]  # full table incl. common prefix + description
    primary_axis: AxisConfig
    secondary_axis: AxisConfig
    format_step_status: StatusFormatter  # progress status-bar text
    format_step_details: StepDetailsFormatter  # Start-from dialog text
