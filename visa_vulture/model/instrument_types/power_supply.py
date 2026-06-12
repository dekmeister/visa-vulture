"""Power-supply instrument type: step dataclass, field specs, executor, view spec,
and the assembled descriptor — everything specific to this one type.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from ...view_specs import AxisConfig, ColumnSpec, InstrumentViewSpec
from ...instruments import BaseInstrument, PowerSupply
from ..test_plan import TestPlan, TestStep
from .descriptor import InstrumentTypeDescriptor
from .executor import StepExecutor
from .fields import SoftLimitSpec, StepFieldSpec, make_columns

logger = logging.getLogger(__name__)

INSTRUMENT_TYPE_POWER_SUPPLY = "power_supply"


@dataclass
class PowerSupplyTestStep(TestStep):
    """A single step in a power supply test plan."""

    voltage: float = 0.0
    current: float = 0.0

    def __post_init__(self) -> None:
        """Validate step values."""
        super().__post_init__()
        if self.voltage < 0:
            raise ValueError(f"voltage must be >= 0, got {self.voltage}")
        if self.current < 0:
            raise ValueError(f"current must be >= 0, got {self.current}")


class PowerSupplyStepExecutor(StepExecutor):
    """Applies voltage/current per step; default output-enable/dwell/teardown."""

    def setup(self, instrument: BaseInstrument, plan: TestPlan) -> None:
        self._total_steps = plan.step_count

    def apply_step(self, instrument: BaseInstrument, step: TestStep) -> None:
        if not isinstance(step, PowerSupplyTestStep):
            raise TypeError(f"Expected PowerSupplyTestStep, got {type(step)}")
        power_supply = cast(PowerSupply, instrument)
        logger.info(
            "Executing step %d/%d: V=%.3f, I=%.3f",
            step.step_number,
            self._total_steps,
            step.voltage,
            step.current,
        )
        power_supply.set_voltage(step.voltage)
        power_supply.set_current(step.current)


_POWER_SUPPLY_FIELDS: tuple[StepFieldSpec, ...] = (
    StepFieldSpec(
        name="voltage",
        unit="V",
        hard_min=0.0,
        hard_max=10000.0,
        soft_limits=SoftLimitSpec(
            max_key="voltage_max_v",
            max_default=100.0,
            above_message="exceeds typical lab supply limits",
            config_min=0.0,
        ),
        axis="primary",
    ),
    StepFieldSpec(
        name="current",
        unit="A",
        hard_min=0.0,
        hard_max=1000.0,
        soft_limits=SoftLimitSpec(
            max_key="current_max_a",
            max_default=50.0,
            above_message="exceeds typical lab supply limits",
            config_min=0.0,
        ),
        axis="secondary",
    ),
)


_POWER_SUPPLY_VIEW = InstrumentViewSpec(
    tab_label="Power Supply",
    columns=make_columns(
        ColumnSpec("voltage", "Voltage (V)", 80, lambda s: f"{s.voltage:.2f}"),
        ColumnSpec("current", "Current (A)", 80, lambda s: f"{s.current:.2f}"),
    ),
    primary_axis=AxisConfig(
        label="Voltage (V)",
        color="blue",
        legend_label="Voltage",
        default_scale="linear",
        default_ylim=(0.0, 1.0),
        lower_bound_zero=True,
    ),
    secondary_axis=AxisConfig(
        label="Current (A)",
        color="red",
        legend_label="Current",
        default_scale="linear",
        default_ylim=(0.0, 1.0),
        lower_bound_zero=True,
    ),
    format_step_status=lambda step, current, total: (
        f"Step {current}/{total}: V={step.voltage:.2f}V, I={step.current:.2f}A"
    ),
    format_step_details=lambda step: f"V={step.voltage:.2f}V, I={step.current:.2f}A",
)


POWER_SUPPLY_DESCRIPTOR = InstrumentTypeDescriptor(
    instrument_type=INSTRUMENT_TYPE_POWER_SUPPLY,
    display_name="Power Supply",
    instrument_cls=PowerSupply,
    step_cls=PowerSupplyTestStep,
    fields=_POWER_SUPPLY_FIELDS,
    executor_cls=PowerSupplyStepExecutor,
    view=_POWER_SUPPLY_VIEW,
)
