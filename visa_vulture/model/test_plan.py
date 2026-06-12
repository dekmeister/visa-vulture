"""Test plan data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    # Modulation configs are driver-owned (instruments/modulation.py); TestPlan
    # only references the base type in an annotation, never at runtime. This is a
    # documented deferral — see CLAUDE.md "Adding a New Instrument Type".
    from ..instruments.modulation import ModulationConfig

# This module is intentionally generic: TestStep and TestPlan only. Per-type step
# dataclasses and the INSTRUMENT_TYPE_* constants live in their respective
# model/instrument_types/<type>.py modules.


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
class TestPlan:
    """
    A complete test plan with multiple steps.

    Test plans define sequences of instrument settings to apply
    during a test run. Each step specifies a duration (how long it
    lasts) and the plan computes absolute times as cumulative sums.
    The instrument_type field determines which execution path is used and
    what step types are expected.
    """

    name: str
    instrument_type: str
    steps: Sequence[TestStep] = field(default_factory=list)
    description: str = ""
    modulation_config: ModulationConfig | None = None  # For signal generator plans

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
