"""Instrument-type registry: descriptors, step executors, and built-in types.

A single registry (``INSTRUMENT_TYPE_REGISTRY``) drives generic test execution,
CSV parsing, soft-limit validation, and presentation. Each entry is an
``InstrumentTypeDescriptor`` bundling the instrument class, step dataclass,
declarative field specs, a per-run ``StepExecutor``, and a pure-data view spec.

New instrument types are added by editing the literal registry below (plus an
instrument class, step dataclass, and simulation device). Custom instruments in
the root ``instruments/`` directory cannot add new types; they subclass built-ins.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields as dataclass_fields
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, cast

from ..instruments import BaseInstrument, PowerSupply, SignalGenerator
from ..instrument_specs import (
    AxisConfig,
    ColumnSpec,
    InstrumentViewSpec,
    SoftLimitSpec,
    StepFieldSpec,
    make_columns,
)
from .test_plan import (
    INSTRUMENT_TYPE_POWER_SUPPLY,
    INSTRUMENT_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    TestPlan,
    TestStep,
)

logger = logging.getLogger(__name__)


class StepContext(Protocol):
    """Execution context the model provides to executors during a run.

    Implemented by ``EquipmentModel``. Lets an executor's ``dwell`` perform an
    interruptible (pause/stop aware) wait without knowing about the model.
    """

    def dwell(self, seconds: float) -> None:
        """Interruptible sleep that honours pause and stop requests."""
        ...

    @property
    def stop_requested(self) -> bool:
        """Whether a stop has been requested."""
        ...


class StepExecutor(ABC):
    """Per-run (possibly stateful) executor for one instrument type.

    A fresh instance is created for each ``run_test`` call, so executors may keep
    per-run state (e.g. the signal generator's previous modulation state).
    """

    def setup(self, instrument: BaseInstrument, plan: TestPlan) -> None:
        """Prepare before the step loop. Default: no-op."""

    @abstractmethod
    def apply_step(self, instrument: BaseInstrument, step: TestStep) -> None:
        """Send instrument commands for one step."""

    def on_first_step(self, instrument: BaseInstrument) -> None:
        """Run on the first executed step. Default: enable output.

        Sinks override this to a no-op (they do not drive an output).
        """
        instrument.enable_output()

    def dwell(
        self, instrument: BaseInstrument, step: TestStep, context: StepContext
    ) -> None:
        """Wait for the step's duration. Default: interruptible sleep.

        Sinks override this to sample repeatedly during the step.
        """
        context.dwell(step.duration_seconds)

    def teardown(self, instrument: BaseInstrument, plan: TestPlan) -> None:
        """Clean up after the step loop. Default: disable output if connected."""
        if instrument.is_connected:
            instrument.disable_output()


# (metadata, errors) -> extra TestPlan kwargs (e.g. signal generator modulation).
MetadataParser = Callable[[dict[str, str], list[str]], dict[str, Any]]


@dataclass(frozen=True)
class InstrumentTypeDescriptor:
    """Everything the program needs to support one instrument type."""

    instrument_type: str  # "power_supply" — the single name for this concept
    display_name: str  # "Power Supply"
    instrument_cls: type[BaseInstrument]
    step_cls: type[TestStep]
    fields: tuple[StepFieldSpec, ...]
    executor_cls: type[StepExecutor]
    view: InstrumentViewSpec  # pure data (no Tkinter)
    parse_plan_metadata: MetadataParser | None = None


# --------------------------------------------------------------------------- #
# Built-in executors (reproduce today's behaviour exactly).
# --------------------------------------------------------------------------- #


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


class SignalGeneratorStepExecutor(StepExecutor):
    """Configures modulation once, sets frequency/power per step, toggles
    modulation only on change, and disables modulation before output on teardown.
    """

    def setup(self, instrument: BaseInstrument, plan: TestPlan) -> None:
        self._total_steps = plan.step_count
        self._modulation_config = plan.modulation_config
        self._prev_mod_enabled: bool | None = None

        signal_gen = cast(SignalGenerator, instrument)
        if self._modulation_config is not None:
            logger.info(
                "Configuring modulation: %s",
                self._modulation_config.modulation_type.value,
            )
            signal_gen.configure_modulation(self._modulation_config)
            signal_gen.set_modulation_enabled(self._modulation_config, False)

    def apply_step(self, instrument: BaseInstrument, step: TestStep) -> None:
        if not isinstance(step, SignalGeneratorTestStep):
            raise TypeError(f"Expected SignalGeneratorTestStep, got {type(step)}")
        signal_gen = cast(SignalGenerator, instrument)
        logger.info(
            "Executing step %d/%d: F=%.1f Hz, P=%.2f dBm, Mod=%s",
            step.step_number,
            self._total_steps,
            step.frequency,
            step.power,
            "ON" if step.modulation_enabled else "OFF",
        )
        signal_gen.set_frequency(step.frequency)
        signal_gen.set_power(step.power)

        if self._modulation_config is not None:
            if self._prev_mod_enabled != step.modulation_enabled:
                signal_gen.set_modulation_enabled(
                    self._modulation_config, step.modulation_enabled
                )
                self._prev_mod_enabled = step.modulation_enabled

    def teardown(self, instrument: BaseInstrument, plan: TestPlan) -> None:
        signal_gen = cast(SignalGenerator, instrument)
        if signal_gen.is_connected:
            if self._modulation_config is not None:
                signal_gen.disable_all_modulation()
            signal_gen.disable_output()


# --------------------------------------------------------------------------- #
# Built-in presentation specs (reproduce today's columns/formatting exactly).
# --------------------------------------------------------------------------- #


def _format_sg_frequency(freq: float) -> str:
    """Format a frequency in engineering units (matches the SG table today)."""
    if freq >= 1e9:
        return f"{freq / 1e9:.3f} GHz"
    elif freq >= 1e6:
        return f"{freq / 1e6:.3f} MHz"
    elif freq >= 1e3:
        return f"{freq / 1e3:.3f} kHz"
    else:
        return f"{freq:.1f} Hz"


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


_SIGNAL_GENERATOR_VIEW = InstrumentViewSpec(
    tab_label="Signal Generator",
    columns=make_columns(
        ColumnSpec("frequency", "Frequency", 90, lambda s: _format_sg_frequency(s.frequency)),
        ColumnSpec("power", "Power (dBm)", 80, lambda s: f"{s.power:.1f}"),
        ColumnSpec(
            "modulation",
            "Modulation",
            80,
            lambda s: "Enabled" if s.modulation_enabled else "Disabled",
        ),
    ),
    primary_axis=AxisConfig(
        label="Frequency (Hz)",
        color="green",
        legend_label="Frequency",
        default_scale="log",
        default_ylim=(1.0, 1000.0),
        lower_bound_zero=True,
    ),
    secondary_axis=AxisConfig(
        label="Power (dBm)",
        color="orange",
        legend_label="Power",
        default_scale="linear",
        default_ylim=(-20.0, 10.0),
        lower_bound_zero=False,
        linear_only=True,
    ),
    format_step_status=lambda step, current, total: (
        f"Step {current}/{total}: F={step.frequency / 1e6:.3f} MHz, P={step.power:.1f} dBm"
    ),
    format_step_details=lambda step: f"F={step.frequency:.1f} Hz, P={step.power:.1f} dBm",
)


# --------------------------------------------------------------------------- #
# Built-in field specs. Hard-limit numeric values are inlined here (the
# HARD_LIMIT_* constants in test_plan.py are removed once the reader consumes
# these in Phase 4). Soft-limit JSON keys/defaults/messages match config + reader.
# --------------------------------------------------------------------------- #

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
        ),
        axis="secondary",
    ),
)

_SIGNAL_GENERATOR_FIELDS: tuple[StepFieldSpec, ...] = (
    StepFieldSpec(
        name="frequency",
        unit="Hz",
        hard_min=0.0,
        hard_max=100e12,
        soft_limits=SoftLimitSpec(
            min_key="frequency_min_hz",
            max_key="frequency_max_hz",
            min_default=1.0,
            max_default=50e9,
            below_message="below typical minimum",
            above_message="exceeds typical equipment limits",
        ),
        axis="primary",
    ),
    StepFieldSpec(
        name="power",
        unit="dBm",
        hard_min=-200.0,
        hard_max=60.0,
        soft_limits=SoftLimitSpec(
            min_key="power_min_dbm",
            max_key="power_max_dbm",
            min_default=-100.0,
            max_default=30.0,
            below_message="below typical noise floor",
            above_message="exceeds typical equipment limits",
        ),
        axis="secondary",
    ),
    StepFieldSpec(
        name="modulation_enabled",
        unit="",
        kind="bool",
        required=False,
        default=False,
        hard_min=None,
        hard_max=None,
    ),
)


_BUILTIN_DESCRIPTORS: tuple[InstrumentTypeDescriptor, ...] = (
    InstrumentTypeDescriptor(
        instrument_type=INSTRUMENT_TYPE_POWER_SUPPLY,
        display_name="Power Supply",
        instrument_cls=PowerSupply,
        step_cls=PowerSupplyTestStep,
        fields=_POWER_SUPPLY_FIELDS,
        executor_cls=PowerSupplyStepExecutor,
        view=_POWER_SUPPLY_VIEW,
    ),
    InstrumentTypeDescriptor(
        instrument_type=INSTRUMENT_TYPE_SIGNAL_GENERATOR,
        display_name="Signal Generator",
        instrument_cls=SignalGenerator,
        step_cls=SignalGeneratorTestStep,
        fields=_SIGNAL_GENERATOR_FIELDS,
        executor_cls=SignalGeneratorStepExecutor,
        view=_SIGNAL_GENERATOR_VIEW,
    ),
)


def _check_descriptor_consistency(descriptor: InstrumentTypeDescriptor) -> None:
    """Import-time guard: field-spec names must equal the step class's own fields.

    Compares ``{spec.name}`` against the step dataclass's own (non-inherited)
    fields — ``fields(step_cls)`` minus ``fields(TestStep)``. Catches a future
    session adding a step attribute without a field spec, or vice versa.
    """
    base_names = {f.name for f in dataclass_fields(TestStep)}
    own_names = {f.name for f in dataclass_fields(descriptor.step_cls)} - base_names
    spec_names = {spec.name for spec in descriptor.fields}
    if spec_names != own_names:
        raise ValueError(
            f"Descriptor for '{descriptor.instrument_type}': field specs "
            f"{sorted(spec_names)} do not match {descriptor.step_cls.__name__} "
            f"own fields {sorted(own_names)}"
        )


for _descriptor in _BUILTIN_DESCRIPTORS:
    _check_descriptor_consistency(_descriptor)


# Literal frozen mapping — no register()/mutation helpers. Custom instruments
# cannot add types; new types are added by editing this literal.
INSTRUMENT_TYPE_REGISTRY: Mapping[str, InstrumentTypeDescriptor] = MappingProxyType(
    {d.instrument_type: d for d in _BUILTIN_DESCRIPTORS}
)
