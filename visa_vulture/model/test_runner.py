"""Stateless test-plan execution helpers.

``run_plan`` resolves a plan's instrument-type descriptor, verifies the connected
instrument, and drives setup → step loop → teardown. ``execute_steps`` is the
generic per-step iteration. Both are stateless: all mutable run state (pause/stop
flags, the state machine, callbacks) stays on ``EquipmentModel``, which passes
itself in as the ``StepContext`` and supplies the progress notifier. This module
must never import ``equipment`` — it talks only to the ``StepContext`` protocol
and the callables it is given.
"""

from __future__ import annotations

import logging
from typing import Callable, Mapping, Sequence

from ..instruments import BaseInstrument
from .instrument_types import InstrumentTypeDescriptor, StepContext
from .test_plan import TestPlan, TestStep

logger = logging.getLogger(__name__)

ProgressNotifier = Callable[[int, int, TestStep], None]


def run_plan(
    registry: Mapping[str, InstrumentTypeDescriptor],
    plan: TestPlan,
    instrument: BaseInstrument | None,
    context: StepContext,
    notify_progress: ProgressNotifier,
    start_step: int = 1,
) -> None:
    """Execute a test plan via its instrument-type executor.

    Looks up the descriptor for the plan's instrument type, verifies the
    connected instrument matches, then runs setup → step loop → teardown.
    The per-step ordering (apply → enable output on first step → notify
    progress → dwell) is identical for every instrument type; behaviour
    differences live in the executor.
    """
    descriptor = registry.get(plan.instrument_type)
    if descriptor is None:
        raise RuntimeError(f"Unknown plan type: {plan.instrument_type}")

    if not isinstance(instrument, descriptor.instrument_cls):
        raise RuntimeError(
            f"Connected instrument is not a {descriptor.display_name.lower()}"
        )

    executor = descriptor.executor_cls()

    executor.setup(instrument, plan)

    def apply_step(step: TestStep) -> None:
        executor.apply_step(instrument, step)

    def enable_output() -> None:
        executor.on_first_step(instrument)

    def dwell(step: TestStep) -> None:
        executor.dwell(instrument, step, context)

    execute_steps(
        context,
        notify_progress,
        plan.steps,
        plan.step_count,
        start_step,
        apply_step,
        enable_output,
        dwell,
    )

    executor.teardown(instrument, plan)


def execute_steps(
    context: StepContext,
    notify_progress: ProgressNotifier,
    steps: Sequence[TestStep],
    total_steps: int,
    start_step: int,
    apply_step: Callable[[TestStep], None],
    enable_output: Callable[[], None],
    dwell: Callable[[TestStep], None] | None = None,
) -> None:
    """Execute the common test plan step iteration loop.

    Iterates over sorted steps, skipping steps before start_step. For each step,
    calls apply_step to send instrument-specific commands, enables output on the
    first executed step, notifies progress, and dwells for the step duration.
    Stops early if the context reports a stop request.

    Args:
        context: Execution context supplying ``stop_requested`` and an
            interruptible ``dwell`` (the default per-step wait).
        notify_progress: Called with (current, total, step) after each applied
            step.
        steps: Sequence of test steps to iterate over.
        total_steps: Total number of steps (for progress reporting).
        start_step: 1-based step number to start execution from.
        apply_step: Callable that applies instrument-specific settings for a
            step. Should perform type narrowing, logging, and instrument commands.
        enable_output: Callable that enables the instrument output.
        dwell: Callable invoked with the step to wait for its duration. Defaults
            to an interruptible sleep of the step duration; an executor may supply
            its own (e.g. a sink sampling during dwell).
    """
    sorted_steps = sorted(steps, key=lambda s: s.step_number)

    for step in sorted_steps:
        if step.step_number < start_step:
            continue

        if context.stop_requested:
            logger.info("Test stopped at step %d", step.step_number)
            break

        apply_step(step)

        if step.step_number == start_step:
            enable_output()

        notify_progress(step.step_number, total_steps, step)

        if dwell is not None:
            dwell(step)
        elif step.duration_seconds > 0:
            context.dwell(step.duration_seconds)
