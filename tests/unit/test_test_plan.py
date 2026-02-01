"""Tests for the test plan module."""

import pytest

from visa_vulture.model.test_plan import (
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    TestPlan,
    TestStep,
    ModulationType,
    ModulationConfig,
    AMModulationConfig,
    FMModulationConfig,
)


class TestTestStep:
    """Tests for TestStep base class."""

    def test_step_creation_with_valid_values(self) -> None:
        """TestStep can be created with valid values."""
        step = TestStep(step_number=1, duration_seconds=5.0, description="Test step")
        assert step.step_number == 1
        assert step.duration_seconds == 5.0
        assert step.description == "Test step"

    def test_step_negative_duration_raises_value_error(self) -> None:
        """Negative duration_seconds raises ValueError."""
        with pytest.raises(ValueError, match="duration_seconds must be >= 0"):
            TestStep(step_number=1, duration_seconds=-1.0)

    def test_step_default_description_is_empty(self) -> None:
        """Default description is an empty string."""
        step = TestStep(step_number=1, duration_seconds=0.0)
        assert step.description == ""

    def test_step_zero_duration_is_valid(self) -> None:
        """Zero duration_seconds is valid."""
        step = TestStep(step_number=1, duration_seconds=0.0)
        assert step.duration_seconds == 0.0

    def test_step_default_absolute_time_is_zero(self) -> None:
        """Default absolute_time_seconds is 0.0."""
        step = TestStep(step_number=1, duration_seconds=5.0)
        assert step.absolute_time_seconds == 0.0


class TestPowerSupplyTestStep:
    """Tests for PowerSupplyTestStep."""

    def test_creation_with_valid_values(self) -> None:
        """PowerSupplyTestStep can be created with valid values."""
        step = PowerSupplyTestStep(
            step_number=1,
            duration_seconds=5.0,
            voltage=5.0,
            current=1.0,
            description="Power step",
        )
        assert step.step_number == 1
        assert step.duration_seconds == 5.0
        assert step.voltage == 5.0
        assert step.current == 1.0
        assert step.description == "Power step"

    def test_negative_voltage_raises_value_error(self) -> None:
        """Negative voltage raises ValueError."""
        with pytest.raises(ValueError, match="voltage must be >= 0"):
            PowerSupplyTestStep(step_number=1, duration_seconds=0.0, voltage=-5.0)

    def test_negative_current_raises_value_error(self) -> None:
        """Negative current raises ValueError."""
        with pytest.raises(ValueError, match="current must be >= 0"):
            PowerSupplyTestStep(step_number=1, duration_seconds=0.0, current=-1.0)

    def test_defaults_to_zero_voltage_and_current(self) -> None:
        """Default voltage and current are 0.0."""
        step = PowerSupplyTestStep(step_number=1, duration_seconds=0.0)
        assert step.voltage == 0.0
        assert step.current == 0.0

    def test_inherits_duration_validation(self) -> None:
        """Inherits negative duration validation from parent."""
        with pytest.raises(ValueError, match="duration_seconds must be >= 0"):
            PowerSupplyTestStep(step_number=1, duration_seconds=-1.0, voltage=5.0)


class TestSignalGeneratorTestStep:
    """Tests for SignalGeneratorTestStep."""

    def test_creation_with_valid_values(self) -> None:
        """SignalGeneratorTestStep can be created with valid values."""
        step = SignalGeneratorTestStep(
            step_number=1,
            duration_seconds=5.0,
            frequency=1e6,
            power=0.0,
            description="Signal step",
        )
        assert step.step_number == 1
        assert step.duration_seconds == 5.0
        assert step.frequency == 1e6
        assert step.power == 0.0
        assert step.description == "Signal step"

    def test_negative_frequency_raises_value_error(self) -> None:
        """Negative frequency raises ValueError."""
        with pytest.raises(ValueError, match="frequency must be >= 0"):
            SignalGeneratorTestStep(step_number=1, duration_seconds=0.0, frequency=-1e6)

    def test_power_can_be_negative(self) -> None:
        """Power can be negative (dBm values)."""
        step = SignalGeneratorTestStep(
            step_number=1, duration_seconds=0.0, frequency=1e6, power=-10.0
        )
        assert step.power == -10.0

    def test_defaults_to_zero_frequency_and_power(self) -> None:
        """Default frequency and power are 0.0."""
        step = SignalGeneratorTestStep(step_number=1, duration_seconds=0.0)
        assert step.frequency == 0.0
        assert step.power == 0.0

    def test_inherits_duration_validation(self) -> None:
        """Inherits negative duration validation from parent."""
        with pytest.raises(ValueError, match="duration_seconds must be >= 0"):
            SignalGeneratorTestStep(
                step_number=1, duration_seconds=-1.0, frequency=1e6
            )

    def test_default_modulation_enabled_is_false(self) -> None:
        """Default modulation_enabled is False."""
        step = SignalGeneratorTestStep(step_number=1, duration_seconds=1.0)
        assert step.modulation_enabled is False

    def test_modulation_enabled_can_be_set_true(self) -> None:
        """modulation_enabled can be set to True."""
        step = SignalGeneratorTestStep(
            step_number=1, duration_seconds=1.0, modulation_enabled=True
        )
        assert step.modulation_enabled is True


class TestModulationType:
    """Tests for ModulationType enum."""

    def test_none_value(self) -> None:
        """NONE has correct value."""
        assert ModulationType.NONE.value == "none"

    def test_am_value(self) -> None:
        """AM has correct value."""
        assert ModulationType.AM.value == "am"

    def test_fm_value(self) -> None:
        """FM has correct value."""
        assert ModulationType.FM.value == "fm"


class TestModulationConfig:
    """Tests for ModulationConfig base class."""

    def test_creation_with_valid_values(self) -> None:
        """ModulationConfig can be created with valid values."""
        config = ModulationConfig(
            modulation_type=ModulationType.AM, modulation_frequency=1000.0
        )
        assert config.modulation_type == ModulationType.AM
        assert config.modulation_frequency == 1000.0

    def test_zero_frequency_raises_value_error(self) -> None:
        """Zero modulation_frequency raises ValueError."""
        with pytest.raises(ValueError, match="modulation_frequency must be > 0"):
            ModulationConfig(
                modulation_type=ModulationType.AM, modulation_frequency=0.0
            )

    def test_negative_frequency_raises_value_error(self) -> None:
        """Negative modulation_frequency raises ValueError."""
        with pytest.raises(ValueError, match="modulation_frequency must be > 0"):
            ModulationConfig(
                modulation_type=ModulationType.AM, modulation_frequency=-100.0
            )


class TestAMModulationConfig:
    """Tests for AMModulationConfig class."""

    def test_creation_with_valid_values(self) -> None:
        """AMModulationConfig can be created with valid values."""
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=50.0,
        )
        assert config.modulation_type == ModulationType.AM
        assert config.modulation_frequency == 1000.0
        assert config.depth == 50.0

    def test_default_depth(self) -> None:
        """Default depth is 50.0%."""
        config = AMModulationConfig(
            modulation_type=ModulationType.AM, modulation_frequency=1000.0
        )
        assert config.depth == 50.0

    def test_depth_zero_is_valid(self) -> None:
        """Depth of 0% is valid."""
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=0.0,
        )
        assert config.depth == 0.0

    def test_depth_100_is_valid(self) -> None:
        """Depth of 100% is valid."""
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=100.0,
        )
        assert config.depth == 100.0

    def test_depth_over_100_raises_value_error(self) -> None:
        """Depth over 100% raises ValueError."""
        with pytest.raises(ValueError, match="AM depth must be 0-100%"):
            AMModulationConfig(
                modulation_type=ModulationType.AM,
                modulation_frequency=1000.0,
                depth=150.0,
            )

    def test_negative_depth_raises_value_error(self) -> None:
        """Negative depth raises ValueError."""
        with pytest.raises(ValueError, match="AM depth must be 0-100%"):
            AMModulationConfig(
                modulation_type=ModulationType.AM,
                modulation_frequency=1000.0,
                depth=-10.0,
            )

    def test_inherits_frequency_validation(self) -> None:
        """Inherits modulation_frequency validation from parent."""
        with pytest.raises(ValueError, match="modulation_frequency must be > 0"):
            AMModulationConfig(
                modulation_type=ModulationType.AM,
                modulation_frequency=0.0,
                depth=50.0,
            )


class TestFMModulationConfig:
    """Tests for FMModulationConfig class."""

    def test_creation_with_valid_values(self) -> None:
        """FMModulationConfig can be created with valid values."""
        config = FMModulationConfig(
            modulation_type=ModulationType.FM,
            modulation_frequency=1000.0,
            deviation=5000.0,
        )
        assert config.modulation_type == ModulationType.FM
        assert config.modulation_frequency == 1000.0
        assert config.deviation == 5000.0

    def test_default_deviation(self) -> None:
        """Default deviation is 1000.0 Hz."""
        config = FMModulationConfig(
            modulation_type=ModulationType.FM, modulation_frequency=1000.0
        )
        assert config.deviation == 1000.0

    def test_zero_deviation_raises_value_error(self) -> None:
        """Zero deviation raises ValueError."""
        with pytest.raises(ValueError, match="FM deviation must be > 0"):
            FMModulationConfig(
                modulation_type=ModulationType.FM,
                modulation_frequency=1000.0,
                deviation=0.0,
            )

    def test_negative_deviation_raises_value_error(self) -> None:
        """Negative deviation raises ValueError."""
        with pytest.raises(ValueError, match="FM deviation must be > 0"):
            FMModulationConfig(
                modulation_type=ModulationType.FM,
                modulation_frequency=1000.0,
                deviation=-100.0,
            )

    def test_inherits_frequency_validation(self) -> None:
        """Inherits modulation_frequency validation from parent."""
        with pytest.raises(ValueError, match="modulation_frequency must be > 0"):
            FMModulationConfig(
                modulation_type=ModulationType.FM,
                modulation_frequency=0.0,
                deviation=5000.0,
            )


class TestTestPlanModulationConfig:
    """Tests for TestPlan modulation_config field."""

    def test_default_modulation_config_is_none(self) -> None:
        """Default modulation_config is None."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_SIGNAL_GENERATOR)
        assert plan.modulation_config is None

    def test_modulation_config_can_be_set_am(self) -> None:
        """modulation_config can be set to AMModulationConfig."""
        config = AMModulationConfig(
            modulation_type=ModulationType.AM,
            modulation_frequency=1000.0,
            depth=50.0,
        )
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_SIGNAL_GENERATOR,
            modulation_config=config,
        )
        assert plan.modulation_config is config

    def test_modulation_config_can_be_set_fm(self) -> None:
        """modulation_config can be set to FMModulationConfig."""
        config = FMModulationConfig(
            modulation_type=ModulationType.FM,
            modulation_frequency=1000.0,
            deviation=5000.0,
        )
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_SIGNAL_GENERATOR,
            modulation_config=config,
        )
        assert plan.modulation_config is config


class TestTestPlanProperties:
    """Tests for TestPlan properties."""

    def test_creation_with_name_and_type(self) -> None:
        """TestPlan can be created with name and type."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY)
        assert plan.name == "Test"
        assert plan.plan_type == PLAN_TYPE_POWER_SUPPLY

    def test_total_duration_returns_sum_of_durations(self) -> None:
        """total_duration returns sum of duration_seconds from all steps."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=2.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=5.0),
                PowerSupplyTestStep(step_number=3, duration_seconds=3.0),
            ],
        )
        assert plan.total_duration == 10.0

    def test_total_duration_with_no_steps_is_zero(self) -> None:
        """total_duration is 0.0 when there are no steps."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY)
        assert plan.total_duration == 0.0

    def test_step_count_returns_number_of_steps(self) -> None:
        """step_count returns the number of steps."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=1.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=1.0),
            ],
        )
        assert plan.step_count == 2

    def test_step_count_empty_plan(self) -> None:
        """step_count is 0 for empty plan."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY)
        assert plan.step_count == 0


class TestTestPlanAbsoluteTime:
    """Tests for absolute time computation from durations."""

    def test_absolute_times_computed_from_durations(self) -> None:
        """Absolute times are cumulative sums of durations."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=2.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=3.0),
                PowerSupplyTestStep(step_number=3, duration_seconds=5.0),
            ],
        )
        assert plan.steps[0].absolute_time_seconds == 0.0
        assert plan.steps[1].absolute_time_seconds == 2.0
        assert plan.steps[2].absolute_time_seconds == 5.0

    def test_absolute_times_with_zero_duration(self) -> None:
        """Zero-duration step does not advance absolute time."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=0.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=3.0),
                PowerSupplyTestStep(step_number=3, duration_seconds=2.0),
            ],
        )
        assert plan.steps[0].absolute_time_seconds == 0.0
        assert plan.steps[1].absolute_time_seconds == 0.0
        assert plan.steps[2].absolute_time_seconds == 3.0

    def test_absolute_times_single_step(self) -> None:
        """Single step starts at absolute time 0."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=10.0),
            ],
        )
        assert plan.steps[0].absolute_time_seconds == 0.0


class TestTestPlanGetStep:
    """Tests for TestPlan.get_step method."""

    def test_get_step_by_number(self) -> None:
        """get_step returns the correct step by number."""
        step1 = PowerSupplyTestStep(step_number=1, duration_seconds=1.0, voltage=5.0)
        step2 = PowerSupplyTestStep(step_number=2, duration_seconds=1.0, voltage=10.0)
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[step1, step2],
        )
        assert plan.get_step(1) is step1
        assert plan.get_step(2) is step2

    def test_get_step_returns_none_for_invalid_number(self) -> None:
        """get_step returns None for non-existent step number."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[PowerSupplyTestStep(step_number=1, duration_seconds=1.0)],
        )
        assert plan.get_step(99) is None

    def test_get_step_empty_plan(self) -> None:
        """get_step returns None for empty plan."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY)
        assert plan.get_step(1) is None


class TestTestPlanValidation:
    """Tests for TestPlan.validate method."""

    def test_validate_empty_name_returns_error(self) -> None:
        """Empty name returns validation error."""
        plan = TestPlan(
            name="",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[PowerSupplyTestStep(step_number=1, duration_seconds=1.0)],
        )
        errors = plan.validate()
        assert any("name is required" in e for e in errors)

    def test_validate_no_steps_returns_error(self) -> None:
        """No steps returns validation error."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY, steps=[])
        errors = plan.validate()
        assert any("at least one step" in e for e in errors)

    def test_validate_valid_plan_returns_empty_list(self) -> None:
        """Valid plan returns empty error list."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=1.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=2.0),
                PowerSupplyTestStep(step_number=3, duration_seconds=3.0),
            ],
        )
        errors = plan.validate()
        assert errors == []

    def test_validate_any_duration_combination_is_valid(self) -> None:
        """Any combination of non-negative durations is valid."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=5.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=0.0),
                PowerSupplyTestStep(step_number=3, duration_seconds=10.0),
            ],
        )
        errors = plan.validate()
        assert errors == []


class TestTestPlanStr:
    """Tests for TestPlan string representation."""

    def test_str_representation(self) -> None:
        """String representation includes name, step count, and duration."""
        plan = TestPlan(
            name="My Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, duration_seconds=2.0),
                PowerSupplyTestStep(step_number=2, duration_seconds=3.0),
            ],
        )
        result = str(plan)
        assert "My Test" in result
        assert "2 steps" in result
        assert "5.0s" in result


class TestPlanTypeConstants:
    """Tests for plan type constants."""

    def test_power_supply_constant(self) -> None:
        """PLAN_TYPE_POWER_SUPPLY has correct value."""
        assert PLAN_TYPE_POWER_SUPPLY == "power_supply"

    def test_signal_generator_constant(self) -> None:
        """PLAN_TYPE_SIGNAL_GENERATOR has correct value."""
        assert PLAN_TYPE_SIGNAL_GENERATOR == "signal_generator"


class TestDurationFromStep:
    """Tests for TestPlan.duration_from_step method."""

    def test_from_first_step_equals_total(self, sample_power_supply_plan) -> None:
        """Duration from step 1 equals total duration."""
        assert (
            sample_power_supply_plan.duration_from_step(1)
            == sample_power_supply_plan.total_duration
        )

    def test_from_last_step(self) -> None:
        """Duration from last step equals that step's duration."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(
                    step_number=1, duration_seconds=5.0, voltage=1.0, current=1.0
                ),
                PowerSupplyTestStep(
                    step_number=2, duration_seconds=3.0, voltage=2.0, current=2.0
                ),
            ],
        )
        assert plan.duration_from_step(2) == 3.0

    def test_from_middle_step(self) -> None:
        """Duration from middle step sums remaining steps."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(
                    step_number=1, duration_seconds=5.0, voltage=1.0, current=1.0
                ),
                PowerSupplyTestStep(
                    step_number=2, duration_seconds=3.0, voltage=2.0, current=2.0
                ),
                PowerSupplyTestStep(
                    step_number=3, duration_seconds=7.0, voltage=3.0, current=3.0
                ),
            ],
        )
        assert plan.duration_from_step(2) == 10.0

    def test_from_nonexistent_step(self) -> None:
        """Duration from step beyond range returns 0."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(
                    step_number=1, duration_seconds=5.0, voltage=1.0, current=1.0
                ),
            ],
        )
        assert plan.duration_from_step(99) == 0.0
