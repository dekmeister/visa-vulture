"""Test plan data structures."""

from dataclasses import dataclass, field
from typing import Sequence

# Plan type constants
PLAN_TYPE_POWER_SUPPLY = "power_supply"
PLAN_TYPE_SIGNAL_GENERATOR = "signal_generator"


@dataclass
class TestStep:
    """Base class for test plan steps.

    Contains common elements shared by all instrument-specific test steps.
    This class should not be instantiated directly - use a subclass like
    PowerSupplyTestStep or SignalGeneratorTestStep.
    """

    step_number: int
    duration_seconds: float
    description: str = ""
    absolute_time_seconds: float = 0.0  # Computed by TestPlan

    def __post_init__(self) -> None:
        """Validate common step values."""
        if self.duration_seconds < 0:
            raise ValueError(
                f"duration_seconds must be >= 0, got {self.duration_seconds}"
            )


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


@dataclass
class SignalGeneratorTestStep(TestStep):
    """A single step in a signal generator test plan."""

    frequency: float = 0.0  # Hz
    power: float = 0.0  # dBm (can be negative)

    def __post_init__(self) -> None:
        """Validate step values."""
        super().__post_init__()
        if self.frequency < 0:
            raise ValueError(f"frequency must be >= 0, got {self.frequency}")


@dataclass
class TestPlan:
    """
    A complete test plan with multiple steps.

    Test plans define sequences of instrument settings to apply
    during a test run. Each step specifies a duration (how long it
    lasts) and the plan computes absolute times as cumulative sums.
    The plan_type field determines which execution path is used and
    what step types are expected.
    """

    name: str
    plan_type: str
    steps: Sequence[TestStep] = field(default_factory=list)
    description: str = ""

    def __post_init__(self) -> None:
        """Compute absolute times from step durations."""
        self._compute_absolute_times()

    def _compute_absolute_times(self) -> None:
        """Set absolute_time_seconds on each step as cumulative sum of durations."""
        sorted_steps = sorted(self.steps, key=lambda s: s.step_number)
        cumulative = 0.0
        for step in sorted_steps:
            step.absolute_time_seconds = cumulative
            cumulative += step.duration_seconds

    @property
    def total_duration(self) -> float:
        """Get total test duration in seconds."""
        if not self.steps:
            return 0.0
        return sum(step.duration_seconds for step in self.steps)

    @property
    def step_count(self) -> int:
        """Get number of steps in the plan."""
        return len(self.steps)

    def duration_from_step(self, step_number: int) -> float:
        """
        Get total duration from a given step number to the end of the plan.

        Args:
            step_number: 1-based step number to start from

        Returns:
            Total duration in seconds from step_number onward (inclusive)
        """
        return sum(
            step.duration_seconds
            for step in self.steps
            if step.step_number >= step_number
        )

    def get_step(self, step_number: int) -> TestStep | None:
        """
        Get a step by number.

        Args:
            step_number: 1-based step number

        Returns:
            TestStep or None if not found
        """
        for step in self.steps:
            if step.step_number == step_number:
                return step
        return None

    def validate(self) -> list[str]:
        """
        Validate the test plan.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not self.name:
            errors.append("Test plan name is required")

        if not self.steps:
            errors.append("Test plan must have at least one step")
            return errors

        return errors

    def __str__(self) -> str:
        """String representation."""
        return (
            f"TestPlan('{self.name}', {self.step_count} steps, {self.total_duration}s)"
        )
