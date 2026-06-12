"""Tests for the instrument-type registry, descriptors, and step executors.

These cover the Phase 2 groundwork: the literal registry, the import-time
descriptor/step-dataclass consistency check, the default executor behaviour, and
the sink-shaped executor interface (overridable on_first_step / dwell) wired
through EquipmentModel._execute_plan.
"""

from dataclasses import dataclass
from types import MappingProxyType
from unittest.mock import Mock, call

import pytest

from visa_vulture.view_specs import InstrumentViewSpec
from visa_vulture.instruments import BaseInstrument, PowerSupply, SignalGenerator
from visa_vulture.model import (
    EquipmentModel,
    EquipmentState,
    INSTRUMENT_TYPE_POWER_SUPPLY,
    INSTRUMENT_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    TestPlan,
    TestStep,
)
from visa_vulture.model.instrument_types import (
    INSTRUMENT_TYPE_REGISTRY,
    InstrumentTypeDescriptor,
    PowerSupplyStepExecutor,
    SignalGeneratorStepExecutor,
    StepExecutor,
    StepFieldSpec,
    make_columns,
    _check_descriptor_consistency,
)


def _force_state(model: EquipmentModel, state: EquipmentState) -> None:
    """Force a model into a given state for direct-execution tests."""
    model._state_machine._state = state


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


class TestRegistry:
    def test_registry_has_both_builtin_types(self) -> None:
        assert set(INSTRUMENT_TYPE_REGISTRY) == {
            INSTRUMENT_TYPE_POWER_SUPPLY,
            INSTRUMENT_TYPE_SIGNAL_GENERATOR,
        }

    def test_registry_keys_match_descriptor_type(self) -> None:
        for key, descriptor in INSTRUMENT_TYPE_REGISTRY.items():
            assert key == descriptor.instrument_type

    def test_power_supply_descriptor_wiring(self) -> None:
        d = INSTRUMENT_TYPE_REGISTRY[INSTRUMENT_TYPE_POWER_SUPPLY]
        assert d.display_name == "Power Supply"
        assert d.instrument_cls is PowerSupply
        assert d.step_cls is PowerSupplyTestStep
        assert d.executor_cls is PowerSupplyStepExecutor
        assert {f.name for f in d.fields} == {"voltage", "current"}

    def test_signal_generator_descriptor_wiring(self) -> None:
        d = INSTRUMENT_TYPE_REGISTRY[INSTRUMENT_TYPE_SIGNAL_GENERATOR]
        assert d.display_name == "Signal Generator"
        assert d.instrument_cls is SignalGenerator
        assert d.executor_cls is SignalGeneratorStepExecutor
        assert {f.name for f in d.fields} == {
            "frequency",
            "power",
            "modulation_enabled",
        }

    def test_registry_is_read_only(self) -> None:
        with pytest.raises(TypeError):
            INSTRUMENT_TYPE_REGISTRY["x"] = None  # type: ignore[index]


# --------------------------------------------------------------------------- #
# Descriptor consistency check
# --------------------------------------------------------------------------- #


class TestDescriptorConsistency:
    def test_builtin_descriptors_pass(self) -> None:
        for descriptor in INSTRUMENT_TYPE_REGISTRY.values():
            _check_descriptor_consistency(descriptor)  # should not raise

    def test_mismatched_descriptor_raises(self) -> None:
        view = INSTRUMENT_TYPE_REGISTRY[INSTRUMENT_TYPE_POWER_SUPPLY].view
        bad = InstrumentTypeDescriptor(
            instrument_type="power_supply",
            display_name="Power Supply",
            instrument_cls=PowerSupply,
            step_cls=PowerSupplyTestStep,
            # Missing "current" — does not match the step dataclass own fields.
            fields=(StepFieldSpec(name="voltage", unit="V"),),
            executor_cls=PowerSupplyStepExecutor,
            view=view,
        )
        with pytest.raises(ValueError, match="do not match"):
            _check_descriptor_consistency(bad)


# --------------------------------------------------------------------------- #
# Default StepExecutor behaviour
# --------------------------------------------------------------------------- #


class _ApplyOnlyExecutor(StepExecutor):
    """Minimal executor exercising only the abstract method + defaults."""

    def apply_step(self, instrument: BaseInstrument, step: TestStep) -> None:
        instrument.applied(step)  # type: ignore[attr-defined]


class TestDefaultExecutor:
    def test_on_first_step_enables_output(self) -> None:
        instrument = Mock(spec=BaseInstrument)
        _ApplyOnlyExecutor().on_first_step(instrument)
        instrument.enable_output.assert_called_once_with()

    def test_default_dwell_delegates_to_context(self) -> None:
        instrument = Mock(spec=BaseInstrument)
        context = Mock()
        step = PowerSupplyTestStep(step_number=1, duration_seconds=2.5)
        _ApplyOnlyExecutor().dwell(instrument, step, context)
        context.dwell.assert_called_once_with(2.5)

    def test_teardown_disables_output_when_connected(self) -> None:
        instrument = Mock(spec=BaseInstrument)
        instrument.is_connected = True
        _ApplyOnlyExecutor().teardown(instrument, Mock())
        instrument.disable_output.assert_called_once_with()

    def test_teardown_skips_disable_when_disconnected(self) -> None:
        instrument = Mock(spec=BaseInstrument)
        instrument.is_connected = False
        _ApplyOnlyExecutor().teardown(instrument, Mock())
        instrument.disable_output.assert_not_called()


# --------------------------------------------------------------------------- #
# Sink-shaped executor interface (no data path — smoke test only)
# --------------------------------------------------------------------------- #


@dataclass
class _SinkStep(TestStep):
    """A trivial sink step type (no source fields)."""


class _SinkInstrument(BaseInstrument):
    """Fake sink instrument; output-enable would be wrong for a sink."""

    def connect(self, visa_resource) -> None:  # pragma: no cover - unused
        pass


class _SinkExecutor(StepExecutor):
    """Overrides on_first_step (no output) and dwell (samples during step)."""

    def __init__(self) -> None:
        self.samples: list[int] = []

    def apply_step(self, instrument: BaseInstrument, step: TestStep) -> None:
        pass

    def on_first_step(self, instrument: BaseInstrument) -> None:
        # Sinks do not drive an output — deliberately a no-op.
        pass

    def dwell(self, instrument, step, context) -> None:
        # Sample once per step instead of sleeping.
        self.samples.append(step.step_number)


def _sink_descriptor() -> InstrumentTypeDescriptor:
    view = INSTRUMENT_TYPE_REGISTRY[INSTRUMENT_TYPE_POWER_SUPPLY].view
    return InstrumentTypeDescriptor(
        instrument_type="sink",
        display_name="Sink",
        instrument_cls=_SinkInstrument,
        step_cls=_SinkStep,
        fields=(),
        executor_cls=_SinkExecutor,
        view=view,
    )


class TestSinkExecutorInterface:
    def test_sink_descriptor_is_consistent(self) -> None:
        # _SinkStep adds no fields over TestStep, and fields=() — they match.
        _check_descriptor_consistency(_sink_descriptor())

    def test_execute_plan_honours_sink_overrides(
        self, mock_visa_connection: Mock
    ) -> None:
        descriptor = _sink_descriptor()
        registry = MappingProxyType({"sink": descriptor})
        model = EquipmentModel(mock_visa_connection, instrument_types=registry)
        _force_state(model, EquipmentState.RUNNING)

        instrument = Mock(spec=_SinkInstrument)
        instrument.is_connected = True
        model._instrument = instrument
        model._instrument_type = "sink"
        model._test_plan = TestPlan(
            name="Sink plan",
            instrument_type="sink",
            steps=[
                _SinkStep(step_number=1, duration_seconds=0.0),
                _SinkStep(step_number=2, duration_seconds=0.0),
            ],
        )

        model._execute_plan()

        # on_first_step override means output is never enabled.
        instrument.enable_output.assert_not_called()
        # Default teardown still disables output when connected.
        instrument.disable_output.assert_called_once_with()


# --------------------------------------------------------------------------- #
# View-spec parity spot checks
# --------------------------------------------------------------------------- #


class TestBuiltinViewSpecs:
    def test_power_supply_columns_and_status(self) -> None:
        view: InstrumentViewSpec = INSTRUMENT_TYPE_REGISTRY[
            INSTRUMENT_TYPE_POWER_SUPPLY
        ].view
        assert view.tab_label == "Power Supply"
        headings = [c.heading for c in view.columns]
        assert headings == [
            "Step",
            "Duration (s)",
            "Abs. Time (s)",
            "Voltage (V)",
            "Current (A)",
            "Description",
        ]
        step = PowerSupplyTestStep(
            step_number=2, duration_seconds=1.0, voltage=5.0, current=0.5
        )
        assert view.format_step_status(step, 2, 4) == "Step 2/4: V=5.00V, I=0.50A"
        assert view.format_step_details(step) == "V=5.00V, I=0.50A"

    def test_signal_generator_frequency_formatting(self) -> None:
        view = INSTRUMENT_TYPE_REGISTRY[INSTRUMENT_TYPE_SIGNAL_GENERATOR].view
        freq_col = next(c for c in view.columns if c.column_id == "frequency")
        ghz = Mock(frequency=1.5e9)
        mhz = Mock(frequency=2.0e6)
        khz = Mock(frequency=3.0e3)
        hz = Mock(frequency=50.0)
        assert freq_col.value_fn(ghz) == "1.500 GHz"
        assert freq_col.value_fn(mhz) == "2.000 MHz"
        assert freq_col.value_fn(khz) == "3.000 kHz"
        assert freq_col.value_fn(hz) == "50.0 Hz"

    def test_make_columns_prefix_and_suffix(self) -> None:
        cols = make_columns()
        assert [c.column_id for c in cols] == ["step", "duration", "abs_time", "description"]
