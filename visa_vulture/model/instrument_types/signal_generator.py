"""Signal-generator instrument type: step dataclass, field specs, executor, view
spec, modulation plan-metadata parsers, and the assembled descriptor.

The modulation *configs* themselves are driver-owned (``instruments/modulation.py``);
here we only parse them from CSV metadata and drive the executor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast

from ...view_specs import AxisConfig, ColumnSpec, InstrumentViewSpec
from ...instruments import BaseInstrument, SignalGenerator
from ...instruments.modulation import (
    AMModulationConfig,
    FMModulationConfig,
    ModulationConfig,
    ModulationType,
)
from ..test_plan import TestPlan, TestStep
from .descriptor import InstrumentTypeDescriptor
from .executor import StepExecutor
from .fields import SoftLimitSpec, StepFieldSpec, make_columns

logger = logging.getLogger(__name__)

INSTRUMENT_TYPE_SIGNAL_GENERATOR = "signal_generator"


@dataclass
class SignalGeneratorTestStep(TestStep):
    """A single step in a signal generator test plan."""

    frequency: float = 0.0  # Hz
    power: float = 0.0  # dBm (can be negative)
    modulation_enabled: bool = False  # Per-step modulation toggle

    def __post_init__(self) -> None:
        """Validate step values."""
        super().__post_init__()
        if self.frequency < 0:
            raise ValueError(f"frequency must be >= 0, got {self.frequency}")


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
# Plan-metadata parsers (signal generator modulation).
#
# These live model-side so the SG descriptor can reference its own
# parse_plan_metadata hook without the model importing file_io (the reader
# imports the registry, not vice versa).
# --------------------------------------------------------------------------- #

_MODULATION_TYPE_KEY = "modulation_type"
_MODULATION_FREQUENCY_KEY = "modulation_frequency"
_AM_DEPTH_KEY = "am_depth"
_FM_DEVIATION_KEY = "fm_deviation"
_VALID_MODULATION_TYPES = {"am", "fm"}


def _parse_am_config(
    metadata: dict[str, str], mod_freq: float, errors: list[str]
) -> AMModulationConfig | None:
    """Parse AM-specific configuration from metadata."""
    depth_str = metadata.get(_AM_DEPTH_KEY)
    if not depth_str:
        errors.append(f"Missing required metadata '{_AM_DEPTH_KEY}' for AM modulation")
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
    metadata: dict[str, str], mod_freq: float, errors: list[str]
) -> FMModulationConfig | None:
    """Parse FM-specific configuration from metadata."""
    deviation_str = metadata.get(_FM_DEVIATION_KEY)
    if not deviation_str:
        errors.append(
            f"Missing required metadata '{_FM_DEVIATION_KEY}' for FM modulation"
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


def _parse_modulation_config(
    metadata: dict[str, str], errors: list[str]
) -> ModulationConfig | None:
    """Parse modulation configuration from CSV metadata (None if unspecified)."""
    mod_type_str = metadata.get(_MODULATION_TYPE_KEY)
    if not mod_type_str:
        return None

    if mod_type_str not in _VALID_MODULATION_TYPES:
        errors.append(
            f"Invalid modulation_type '{mod_type_str}'. "
            f"Must be one of: {', '.join(sorted(_VALID_MODULATION_TYPES))}"
        )
        return None

    mod_freq_str = metadata.get(_MODULATION_FREQUENCY_KEY)
    if not mod_freq_str:
        errors.append(
            f"Missing required metadata '{_MODULATION_FREQUENCY_KEY}' "
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

    if mod_type_str == "am":
        return _parse_am_config(metadata, mod_freq, errors)
    elif mod_type_str == "fm":
        return _parse_fm_config(metadata, mod_freq, errors)

    return None


def parse_signal_generator_metadata(
    metadata: dict[str, str], errors: list[str]
) -> dict[str, Any]:
    """SG plan-metadata hook: returns the modulation_config TestPlan kwarg."""
    return {"modulation_config": _parse_modulation_config(metadata, errors)}


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
            config_min=0.0,
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


SIGNAL_GENERATOR_DESCRIPTOR = InstrumentTypeDescriptor(
    instrument_type=INSTRUMENT_TYPE_SIGNAL_GENERATOR,
    display_name="Signal Generator",
    instrument_cls=SignalGenerator,
    step_cls=SignalGeneratorTestStep,
    fields=_SIGNAL_GENERATOR_FIELDS,
    executor_cls=SignalGeneratorStepExecutor,
    view=_SIGNAL_GENERATOR_VIEW,
    parse_plan_metadata=parse_signal_generator_metadata,
)
