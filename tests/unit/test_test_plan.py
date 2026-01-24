"""Tests for the test plan module."""

import pytest

from src.model.test_plan import (
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    TestPlan,
    TestStep,
)


class TestTestStep:
    """Tests for TestStep base class."""

    def test_step_creation_with_valid_values(self) -> None:
        """TestStep can be created with valid values."""
        step = TestStep(step_number=1, time_seconds=0.0, description="Test step")
        assert step.step_number == 1
        assert step.time_seconds == 0.0
        assert step.description == "Test step"

    def test_step_negative_time_raises_value_error(self) -> None:
        """Negative time_seconds raises ValueError."""
        with pytest.raises(ValueError, match="time_seconds must be >= 0"):
            TestStep(step_number=1, time_seconds=-1.0)

    def test_step_default_description_is_empty(self) -> None:
        """Default description is an empty string."""
        step = TestStep(step_number=1, time_seconds=0.0)
        assert step.description == ""

    def test_step_zero_time_is_valid(self) -> None:
        """Zero time_seconds is valid."""
        step = TestStep(step_number=1, time_seconds=0.0)
        assert step.time_seconds == 0.0


class TestPowerSupplyTestStep:
    """Tests for PowerSupplyTestStep."""

    def test_creation_with_valid_values(self) -> None:
        """PowerSupplyTestStep can be created with valid values."""
        step = PowerSupplyTestStep(
            step_number=1,
            time_seconds=0.0,
            voltage=5.0,
            current=1.0,
            description="Power step",
        )
        assert step.step_number == 1
        assert step.time_seconds == 0.0
        assert step.voltage == 5.0
        assert step.current == 1.0
        assert step.description == "Power step"

    def test_negative_voltage_raises_value_error(self) -> None:
        """Negative voltage raises ValueError."""
        with pytest.raises(ValueError, match="voltage must be >= 0"):
            PowerSupplyTestStep(step_number=1, time_seconds=0.0, voltage=-5.0)

    def test_negative_current_raises_value_error(self) -> None:
        """Negative current raises ValueError."""
        with pytest.raises(ValueError, match="current must be >= 0"):
            PowerSupplyTestStep(step_number=1, time_seconds=0.0, current=-1.0)

    def test_defaults_to_zero_voltage_and_current(self) -> None:
        """Default voltage and current are 0.0."""
        step = PowerSupplyTestStep(step_number=1, time_seconds=0.0)
        assert step.voltage == 0.0
        assert step.current == 0.0

    def test_inherits_time_validation(self) -> None:
        """Inherits negative time validation from parent."""
        with pytest.raises(ValueError, match="time_seconds must be >= 0"):
            PowerSupplyTestStep(step_number=1, time_seconds=-1.0, voltage=5.0)


class TestSignalGeneratorTestStep:
    """Tests for SignalGeneratorTestStep."""

    def test_creation_with_valid_values(self) -> None:
        """SignalGeneratorTestStep can be created with valid values."""
        step = SignalGeneratorTestStep(
            step_number=1,
            time_seconds=0.0,
            frequency=1e6,
            power=0.0,
            description="Signal step",
        )
        assert step.step_number == 1
        assert step.time_seconds == 0.0
        assert step.frequency == 1e6
        assert step.power == 0.0
        assert step.description == "Signal step"

    def test_negative_frequency_raises_value_error(self) -> None:
        """Negative frequency raises ValueError."""
        with pytest.raises(ValueError, match="frequency must be >= 0"):
            SignalGeneratorTestStep(step_number=1, time_seconds=0.0, frequency=-1e6)

    def test_power_can_be_negative(self) -> None:
        """Power can be negative (dBm values)."""
        step = SignalGeneratorTestStep(
            step_number=1, time_seconds=0.0, frequency=1e6, power=-10.0
        )
        assert step.power == -10.0

    def test_defaults_to_zero_frequency_and_power(self) -> None:
        """Default frequency and power are 0.0."""
        step = SignalGeneratorTestStep(step_number=1, time_seconds=0.0)
        assert step.frequency == 0.0
        assert step.power == 0.0

    def test_inherits_time_validation(self) -> None:
        """Inherits negative time validation from parent."""
        with pytest.raises(ValueError, match="time_seconds must be >= 0"):
            SignalGeneratorTestStep(step_number=1, time_seconds=-1.0, frequency=1e6)


class TestTestPlanProperties:
    """Tests for TestPlan properties."""

    def test_creation_with_name_and_type(self) -> None:
        """TestPlan can be created with name and type."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY)
        assert plan.name == "Test"
        assert plan.plan_type == PLAN_TYPE_POWER_SUPPLY

    def test_total_duration_returns_max_time(self) -> None:
        """total_duration returns maximum time_seconds from steps."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, time_seconds=0.0),
                PowerSupplyTestStep(step_number=2, time_seconds=5.0),
                PowerSupplyTestStep(step_number=3, time_seconds=3.0),
            ],
        )
        assert plan.total_duration == 5.0

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
                PowerSupplyTestStep(step_number=1, time_seconds=0.0),
                PowerSupplyTestStep(step_number=2, time_seconds=1.0),
            ],
        )
        assert plan.step_count == 2

    def test_step_count_empty_plan(self) -> None:
        """step_count is 0 for empty plan."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY)
        assert plan.step_count == 0


class TestTestPlanGetStep:
    """Tests for TestPlan.get_step method."""

    def test_get_step_by_number(self) -> None:
        """get_step returns the correct step by number."""
        step1 = PowerSupplyTestStep(step_number=1, time_seconds=0.0, voltage=5.0)
        step2 = PowerSupplyTestStep(step_number=2, time_seconds=1.0, voltage=10.0)
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
            steps=[PowerSupplyTestStep(step_number=1, time_seconds=0.0)],
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
            steps=[PowerSupplyTestStep(step_number=1, time_seconds=0.0)],
        )
        errors = plan.validate()
        assert any("name is required" in e for e in errors)

    def test_validate_no_steps_returns_error(self) -> None:
        """No steps returns validation error."""
        plan = TestPlan(name="Test", plan_type=PLAN_TYPE_POWER_SUPPLY, steps=[])
        errors = plan.validate()
        assert any("at least one step" in e for e in errors)

    def test_validate_decreasing_times_returns_error(self) -> None:
        """Decreasing times returns validation error."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, time_seconds=0.0),
                PowerSupplyTestStep(step_number=2, time_seconds=5.0),
                PowerSupplyTestStep(step_number=3, time_seconds=3.0),  # Decreasing
            ],
        )
        errors = plan.validate()
        assert any("non-decreasing" in e for e in errors)

    def test_validate_valid_plan_returns_empty_list(self) -> None:
        """Valid plan returns empty error list."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, time_seconds=0.0),
                PowerSupplyTestStep(step_number=2, time_seconds=1.0),
                PowerSupplyTestStep(step_number=3, time_seconds=2.0),
            ],
        )
        errors = plan.validate()
        assert errors == []

    def test_validate_equal_times_is_valid(self) -> None:
        """Equal consecutive times are valid (non-decreasing)."""
        plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(step_number=1, time_seconds=0.0),
                PowerSupplyTestStep(step_number=2, time_seconds=1.0),
                PowerSupplyTestStep(step_number=3, time_seconds=1.0),  # Same as step 2
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
                PowerSupplyTestStep(step_number=1, time_seconds=0.0),
                PowerSupplyTestStep(step_number=2, time_seconds=5.0),
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
