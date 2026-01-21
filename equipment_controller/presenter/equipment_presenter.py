"""Equipment presenter - coordinates model and view."""

import logging
from typing import Union

from ..file_io import read_test_plan
from ..model import (
    EquipmentModel,
    EquipmentState,
    TestStep,
    SignalGeneratorTestStep,
    SignalGeneratorTestPlan,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
)
from ..utils import BackgroundTaskRunner
from ..view import MainWindow

logger = logging.getLogger(__name__)

# Type alias for any test step
AnyTestStep = Union[TestStep, SignalGeneratorTestStep]


class EquipmentPresenter:
    """
    Coordinates model and view.

    Wires view callbacks to model operations.
    Manages background thread execution for VISA operations.
    Updates view based on model state changes.
    """

    def __init__(self, model: EquipmentModel, view: MainWindow, poll_interval_ms: int = 100):
        """
        Initialize presenter.

        Args:
            model: Equipment model
            view: Main window view
            poll_interval_ms: Polling interval for background task results
        """
        self._model = model
        self._view = view
        self._poll_interval_ms = poll_interval_ms

        # Background task runner
        self._task_runner = BackgroundTaskRunner(view.schedule)

        # Wire everything up
        self._wire_callbacks()
        self._task_runner.start(poll_interval_ms)

        # Initial view state
        self._update_view_for_state(self._model.state)

        logger.info("EquipmentPresenter initialized")

    def _wire_callbacks(self) -> None:
        """Wire view callbacks and model callbacks."""
        # View callbacks
        self._view.set_on_connect(self._handle_connect)
        self._view.set_on_disconnect(self._handle_disconnect)
        self._view.set_on_load_test_plan(self._handle_load_test_plan)
        self._view.set_on_run(self._handle_run)
        self._view.set_on_stop(self._handle_stop)

        # Model callbacks
        self._model.register_state_callback(self._on_state_changed)
        self._model.register_progress_callback(self._on_test_progress)
        self._model.register_complete_callback(self._on_test_complete)

    # View callback handlers

    def _handle_connect(self) -> None:
        """Handle connect button."""
        logger.info("Connect requested")
        self._view.set_status("Connecting...")

        def task():
            self._model.connect()

        def on_complete(result):
            if isinstance(result, Exception) or (hasattr(result, 'success') and not result.success):
                error = result.error if hasattr(result, 'error') else result
                self._view.show_error("Connection Error", str(error))
                self._view.set_status("Connection failed")
            else:
                self._view.set_connection_status(True)
                self._view.set_status("Connected")

        self._task_runner.run_task(task, on_complete)

    def _handle_disconnect(self) -> None:
        """Handle disconnect button."""
        logger.info("Disconnect requested")
        self._view.set_status("Disconnecting...")

        def task():
            self._model.disconnect()

        def on_complete(result):
            self._view.set_connection_status(False)
            self._view.set_status("Disconnected")

        self._task_runner.run_task(task, on_complete)

    def _handle_load_test_plan(self, file_path: str) -> None:
        """Handle load test plan button."""
        logger.info("Loading test plan: %s", file_path)

        test_plan, errors = read_test_plan(file_path)

        if errors:
            error_msg = "\n".join(errors)
            self._view.show_error("Test Plan Error", error_msg)
            logger.error("Test plan load failed: %s", error_msg)
            return

        if test_plan is None:
            self._view.show_error("Test Plan Error", "Failed to load test plan")
            return

        try:
            self._model.load_test_plan(test_plan)
            self._view.set_test_plan_name(test_plan.name)
            self._view.set_status(f"Loaded: {test_plan}")

            # Handle plot based on plan type
            if test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                # Signal generator plan
                self._view.signal_gen_plot_panel.clear()
                self._view.signal_gen_plot_panel.set_title(test_plan.name)
                self._view.show_signal_generator_plot()

                # Load test plan preview (show full trajectory)
                if isinstance(test_plan, SignalGeneratorTestPlan):
                    times = [s.time_seconds for s in test_plan.steps]
                    freqs = [s.frequency for s in test_plan.steps]
                    powers = [s.power for s in test_plan.steps]
                    self._view.signal_gen_plot_panel.load_test_plan_preview(times, freqs, powers)
            else:
                # Power supply plan
                self._view.plot_panel.clear()
                self._view.plot_panel.set_title(test_plan.name)
                self._view.show_power_supply_plot()

            # Enable run button if connected
            if self._model.state == EquipmentState.IDLE:
                self._view.set_buttons_for_state("IDLE")

            logger.info("Test plan loaded: %s", test_plan)

        except ValueError as e:
            self._view.show_error("Test Plan Error", str(e))
            logger.error("Test plan validation failed: %s", e)

    def _handle_run(self) -> None:
        """Handle run button."""
        logger.info("Run requested")

        if self._model.test_plan is None:
            self._view.show_error("Error", "No test plan loaded")
            return

        self._view.set_status("Running test...")
        self._view.set_progress(0, self._model.test_plan.step_count)

        # Clear position indicator but keep the plan preview for signal generator
        if self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            self._view.signal_gen_plot_panel.clear_position()
        else:
            self._view.plot_panel.clear()

        def task():
            self._model.run_test()

        def on_complete(result):
            # State change callback handles UI updates
            pass

        self._task_runner.run_task(task, on_complete)

    def _handle_stop(self) -> None:
        """Handle stop button."""
        logger.info("Stop requested")
        self._model.stop_test()
        self._view.set_status("Stopping...")

    # Model callback handlers

    def _on_state_changed(self, old_state: EquipmentState, new_state: EquipmentState) -> None:
        """Handle model state change."""
        logger.debug("State changed: %s -> %s", old_state.name, new_state.name)

        # Schedule view update on main thread
        self._view.schedule(0, lambda: self._update_view_for_state(new_state))

    def _on_test_progress(self, current: int, total: int, step: AnyTestStep) -> None:
        """Handle test progress update."""
        # Schedule view update on main thread
        def update():
            self._view.set_progress(current, total)

            if isinstance(step, SignalGeneratorTestStep):
                # Signal generator step
                self._view.set_status(
                    f"Step {current}/{total}: F={step.frequency/1e6:.3f} MHz, P={step.power:.1f} dBm"
                )
                # Update position indicator on the plot
                self._view.signal_gen_plot_panel.set_current_position(step.time_seconds)
            else:
                # Power supply step
                self._view.set_status(
                    f"Step {current}/{total}: V={step.voltage:.2f}V, I={step.current:.2f}A"
                )
                # Add point to plot
                self._view.plot_panel.add_point(step.time_seconds, step.voltage, step.current)

        self._view.schedule(0, update)

    def _on_test_complete(self, success: bool, message: str) -> None:
        """Handle test completion."""
        def update():
            if success:
                self._view.set_status(message)
                self._view.show_info("Test Complete", message)
            else:
                self._view.set_status(f"Error: {message}")
                self._view.show_error("Test Error", message)

            self._view.set_progress(0, 0)

            # Clear position indicator for signal generator
            if self._model.test_plan and self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                self._view.signal_gen_plot_panel.clear_position()

        self._view.schedule(0, update)

    def _update_view_for_state(self, state: EquipmentState) -> None:
        """Update view based on current state."""
        state_name = state.name

        self._view.set_state_display(state_name)
        self._view.set_buttons_for_state(state_name)

        # Update connection indicator
        connected = state in (EquipmentState.IDLE, EquipmentState.RUNNING)
        self._view.set_connection_status(connected)

        # Check if run should be enabled (need both connection and test plan)
        if state == EquipmentState.IDLE and self._model.test_plan is None:
            # Can't run without a test plan, but leave button state for visual feedback
            pass

    def shutdown(self) -> None:
        """Clean shutdown of presenter."""
        logger.info("EquipmentPresenter shutting down")
        self._task_runner.stop()

        # Disconnect if connected
        if self._model.state in (EquipmentState.IDLE, EquipmentState.RUNNING):
            try:
                self._model.disconnect()
            except Exception as e:
                logger.warning("Error during disconnect on shutdown: %s", e)
