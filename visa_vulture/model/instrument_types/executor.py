"""Per-run step-execution framework: the context the model exposes to executors
and the executor base class itself. Generic — no per-type content.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Protocol

from ...instruments import BaseInstrument
from ..test_plan import TestPlan, TestStep


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
