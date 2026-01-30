"""Equipment presenter - coordinates model and view."""

import logging
import time

from ..file_io import read_test_plan
from ..model import (
    EquipmentModel,
    EquipmentState,
    TestStep,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
)
from ..utils import BackgroundTaskRunner
from ..view import MainWindow

logger = logging.getLogger(__name__)


class EquipmentPresenter:
    """
    Coordinates model and view.

    Wires view callbacks to model operations.
    Manages background thread execution for VISA operations.
    Updates view based on model state changes.
    """

    def __init__(
        self, model: EquipmentModel, view: MainWindow, poll_interval_ms: int = 100
    ):
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

        # Runtime timer state
        self._runtime_timer_id: str | None = None
        self._run_start_time: float | None = None
        self._elapsed_at_pause: float | None = None
        self._partial_total_duration: float | None = None

        # Pending "start from" state (step, remaining_duration)
        self._pending_start_from: tuple[int, float] | None = None

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
        self._view.set_on_pause(self._handle_pause)
        self._view.set_on_start_from(self._handle_start_from)

        # Table selection callbacks
        self._view.ps_table.register_selection_callback(
            self._on_table_selection_changed
        )
        self._view.sg_table.register_selection_callback(
            self._on_table_selection_changed
        )

        # Model callbacks
        self._model.register_state_callback(self._on_state_changed)
        self._model.register_progress_callback(self._on_test_progress)
        self._model.register_complete_callback(self._on_test_complete)

    # View callback handlers

    def _handle_connect(self) -> None:
        """Handle connect button - opens resource manager dialog."""
        from ..view import ResourceManagerDialog

        logger.info("Connect requested - opening resource manager")

        # Create and configure dialog
        dialog = ResourceManagerDialog(self._view._root)
        dialog.set_on_scan(lambda: self._handle_dialog_scan(dialog))
        dialog.set_on_identify(lambda: self._handle_dialog_identify(dialog))

        # Show dialog and wait for result
        result = dialog.show()

        if result is None:
            logger.info("Connection cancelled")
            return

        resource_address, instrument_type = result
        self._connect_to_resource(resource_address, instrument_type)

    def _handle_dialog_scan(self, dialog) -> None:
        """Handle Scan button in resource manager dialog."""
        dialog.set_status("Scanning...")
        dialog.set_buttons_enabled(False, False, False)

        def task():
            return self._model.scan_resources()

        def on_complete(result):
            if isinstance(result, Exception):
                dialog.set_status(f"Scan failed: {result}")
                dialog.set_resources([])
                dialog.set_buttons_enabled(True, False, False)
            else:
                dialog.set_resources(result)
                has_resources = len(result) > 0
                dialog.set_status(f"Found {len(result)} resource(s)")
                dialog.set_buttons_enabled(True, has_resources, has_resources)

        self._task_runner.run_task(task, on_complete)

    def _handle_dialog_identify(self, dialog) -> None:
        """Handle Identify button - query *IDN? on each resource."""
        resources = dialog.get_resources()
        if not resources:
            dialog.set_status("No resources to identify")
            return

        dialog.set_status("Identifying resources...")
        dialog.set_buttons_enabled(False, False, False)

        def task():
            results = {}
            for resource in resources:
                results[resource] = self._model.identify_resource(resource)
            return results

        def on_complete(result):
            if isinstance(result, Exception):
                dialog.set_status(f"Identify failed: {result}")
            else:
                for resource, idn in result.items():
                    dialog.set_resource_identification(resource, idn)
                dialog.set_status("Identification complete")
            dialog.set_buttons_enabled(True, True, True)

        self._task_runner.run_task(task, on_complete)

    def _connect_to_resource(self, resource_address: str, instrument_type: str) -> None:
        """Connect to selected resource."""
        logger.info("Connecting to %s as %s", resource_address, instrument_type)
        self._view.set_status(f"Connecting to {resource_address}...")

        def task():
            self._model.connect_instrument(resource_address, instrument_type)

        def on_complete(result):
            if isinstance(result, Exception):
                self._view.show_error("Connection Error", str(result))
                self._view.set_status("Connection failed")
            else:
                self._view.set_connection_status(True)
                self._view.set_status("Connected")
                self._update_instrument_display()
                # Show only relevant tab
                if instrument_type == "power_supply":
                    self._view.show_power_supply_tab_only()
                else:
                    self._view.show_signal_generator_tab_only()

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
            self._view.set_instrument_display(None, None)
            # Show both tabs when disconnected
            self._view.show_all_tabs()

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

            # Handle plot and table based on plan type
            if test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                # Signal generator plan
                self._view.signal_gen_plot_panel.clear()
                self._view.signal_gen_plot_panel.set_title(test_plan.name)
                self._view.show_signal_generator_plot()

                # Load test plan preview (show full trajectory)
                # Steps are SignalGeneratorTestStep when plan_type is signal_generator
                times = [s.absolute_time_seconds for s in test_plan.steps]
                freqs = [s.frequency for s in test_plan.steps]  # type: ignore[attr-defined]
                powers = [s.power for s in test_plan.steps]  # type: ignore[attr-defined]
                self._view.signal_gen_plot_panel.load_test_plan_preview(
                    times, freqs, powers
                )

                # Load test steps into table
                self._view.sg_table.load_steps(test_plan.steps)
            else:
                # Power supply plan
                self._view.power_supply_plot_panel.clear()
                self._view.power_supply_plot_panel.set_title(test_plan.name)
                self._view.show_power_supply_plot()

                # Load test plan preview (show full trajectory)
                # Steps are PowerSupplyTestStep when plan_type is power_supply
                times = [s.absolute_time_seconds for s in test_plan.steps]
                voltages = [s.voltage for s in test_plan.steps]  # type: ignore[attr-defined]
                currents = [s.current for s in test_plan.steps]  # type: ignore[attr-defined]
                self._view.power_supply_plot_panel.load_test_plan_preview(
                    times, voltages, currents
                )

                # Load test steps into table
                self._view.ps_table.load_steps(test_plan.steps)

            # Enable run button if connected
            if self._model.state == EquipmentState.IDLE:
                self._view.set_buttons_for_state("IDLE")

            # Show total duration as remaining time
            self._view.set_remaining_time_display(test_plan.total_duration)

            logger.info("Test plan loaded: %s", test_plan)

        except ValueError as e:
            self._view.show_error("Test Plan Error", str(e))
            logger.error("Test plan validation failed: %s", e)

    def _handle_run(self) -> None:
        """Handle run button (also handles resume when paused)."""
        # Handle resume from paused state
        if self._model.state == EquipmentState.PAUSED:
            logger.info("Resume requested")
            self._model.resume_test()
            self._view.set_status("Resuming test...")

            # Restore runtime timer from where we left off
            if self._elapsed_at_pause is not None:
                self._run_start_time = time.time() - self._elapsed_at_pause
                self._elapsed_at_pause = None
                self._start_runtime_timer()
            return

        logger.info("Run requested")

        if self._model.test_plan is None:
            self._view.show_error("Error", "No test plan loaded")
            return

        # Verify instrument type matches plan type
        plan_type = self._model.test_plan.plan_type
        instrument_type = self._model.instrument_type
        if plan_type == PLAN_TYPE_POWER_SUPPLY and instrument_type != "power_supply":
            self._view.show_error(
                "Instrument Mismatch",
                "Power supply test plan requires a power supply instrument",
            )
            return
        elif (
            plan_type == PLAN_TYPE_SIGNAL_GENERATOR
            and instrument_type != "signal_generator"
        ):
            self._view.show_error(
                "Instrument Mismatch",
                "Signal generator test plan requires a signal generator instrument",
            )
            return

        self._view.set_status("Running test...")

        # Start runtime timer
        self._partial_total_duration = None
        self._run_start_time = time.time()
        self._start_runtime_timer()

        # Clear position indicator but keep the plan preview for both plot types
        if self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            self._view.signal_gen_plot_panel.clear_position()
        else:
            self._view.power_supply_plot_panel.clear_position()

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
        # Clear pause state if stopping from paused
        self._elapsed_at_pause = None

    def _handle_pause(self) -> None:
        """Handle pause button."""
        logger.info("Pause requested")
        self._model.pause_test()
        self._view.set_status("Pausing...")

    def _on_table_selection_changed(self, step_number: int | None) -> None:
        """Handle table row selection change to enable/disable Start from button."""
        state = self._model.state
        has_plan = self._model.test_plan is not None
        if (
            state in (EquipmentState.IDLE, EquipmentState.PAUSED)
            and step_number is not None
            and has_plan
        ):
            self._view.set_start_from_enabled(True)
        else:
            self._view.set_start_from_enabled(False)

    def _handle_start_from(self) -> None:
        """Handle Start from / Resume from button click."""
        selected_step = self._view.get_active_table_selected_step()
        if selected_step is None:
            self._view.show_error("Error", "No test step selected")
            return

        if self._model.test_plan is None:
            self._view.show_error("Error", "No test plan loaded")
            return

        step = self._model.test_plan.get_step(selected_step)
        if step is None:
            self._view.show_error("Error", f"Step {selected_step} not found")
            return

        # Build confirmation message
        remaining_duration = self._model.test_plan.duration_from_step(selected_step)
        total_steps = self._model.test_plan.step_count
        steps_to_run = total_steps - selected_step + 1

        if isinstance(step, PowerSupplyTestStep):
            step_details = f"V={step.voltage:.2f}V, I={step.current:.2f}A"
        elif isinstance(step, SignalGeneratorTestStep):
            step_details = f"F={step.frequency:.1f} Hz, P={step.power:.1f} dBm"
        else:
            step_details = f"Duration={step.duration_seconds}s"

        is_paused = self._model.state == EquipmentState.PAUSED
        action = "Resume from" if is_paused else "Start from"

        remaining_int = max(0, int(remaining_duration))
        minutes = remaining_int // 60
        seconds = remaining_int % 60
        duration_str = f"{minutes:02d}:{seconds:02d}"

        message = (
            f"{action} step {selected_step}/{total_steps}?\n\n"
            f"Step details: {step_details}\n"
            f"Description: {step.description}\n"
            f"Steps remaining: {steps_to_run}\n"
            f"Estimated duration: {duration_str}"
        )

        if not self._view.show_confirmation(
            f"{action} Step {selected_step}", message
        ):
            return

        if is_paused:
            self._pending_start_from = (selected_step, remaining_duration)
            self._model.stop_test()
            self._elapsed_at_pause = None
            self._view.set_status(f"Restarting from step {selected_step}...")
            return

        # IDLE state - start directly
        self._execute_start_from(selected_step, remaining_duration)

    def _execute_start_from(self, start_step: int, remaining_duration: float) -> None:
        """Execute test from a specific step with adjusted timer."""
        logger.info("Starting test from step %d", start_step)
        self._view.set_status(f"Running from step {start_step}...")

        self._partial_total_duration = remaining_duration
        self._run_start_time = time.time()
        self._start_runtime_timer()

        if (
            self._model.test_plan is not None
            and self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR
        ):
            self._view.signal_gen_plot_panel.clear_position()
        else:
            self._view.power_supply_plot_panel.clear_position()

        def task():
            self._model.run_test_from_step(start_step)

        def on_complete(result):
            pass

        self._task_runner.run_task(task, on_complete)

    # Model callback handlers

    def _on_state_changed(
        self, old_state: EquipmentState, new_state: EquipmentState
    ) -> None:
        """Handle model state change."""
        logger.debug("State changed: %s -> %s", old_state.name, new_state.name)

        # Handle timer when leaving RUNNING state
        if old_state == EquipmentState.RUNNING and new_state != EquipmentState.RUNNING:
            if new_state == EquipmentState.PAUSED:
                # Pausing - save elapsed time and stop timer
                if self._run_start_time is not None:
                    self._elapsed_at_pause = time.time() - self._run_start_time
                self._view.schedule(0, self._stop_runtime_timer_for_pause)
            else:
                # Actually stopping
                self._elapsed_at_pause = None
                self._view.schedule(0, self._stop_runtime_timer)

        # Clear pause state when transitioning from PAUSED to IDLE (stop while paused)
        if old_state == EquipmentState.PAUSED and new_state == EquipmentState.IDLE:
            self._elapsed_at_pause = None

        # Handle pending "start from" operation (after stopping a paused run)
        if new_state == EquipmentState.IDLE and self._pending_start_from is not None:
            start_step, remaining_duration = self._pending_start_from
            self._pending_start_from = None
            self._view.schedule(
                50,
                lambda s=start_step, d=remaining_duration: self._execute_start_from(
                    s, d
                ),
            )

        # Schedule view update on main thread
        self._view.schedule(0, lambda: self._update_view_for_state(new_state))

    def _on_test_progress(self, current: int, total: int, step: TestStep) -> None:
        """Handle test progress update."""

        # Schedule view update on main thread
        def update():
            if isinstance(step, SignalGeneratorTestStep):
                # Signal generator step
                self._view.set_status(
                    f"Step {current}/{total}: F={step.frequency/1e6:.3f} MHz, P={step.power:.1f} dBm"
                )
                # Update position indicator on the plot
                self._view.signal_gen_plot_panel.set_current_position(
                    step.absolute_time_seconds
                )
                # Highlight current row in table
                self._view.sg_table.highlight_step(step.step_number)
            elif isinstance(step, PowerSupplyTestStep):
                # Power supply step
                self._view.set_status(
                    f"Step {current}/{total}: V={step.voltage:.2f}V, I={step.current:.2f}A"
                )
                # Update position indicator on the plot
                self._view.power_supply_plot_panel.set_current_position(
                    step.absolute_time_seconds
                )
                # Highlight current row in table
                self._view.ps_table.highlight_step(step.step_number)

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

            # Clear position indicators and table highlighting
            if (
                self._model.test_plan
                and self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR
            ):
                self._view.signal_gen_plot_panel.clear_position()
                self._view.sg_table.clear_highlight()
            else:
                self._view.power_supply_plot_panel.clear_position()
                self._view.ps_table.clear_highlight()

        self._view.schedule(0, update)

    def _update_instrument_display(self) -> None:
        """Update instrument identification display."""
        if self._model.state not in (
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        ):
            self._view.set_instrument_display(None, None)
            return

        # Single instrument - no need to check tab
        model_name, tooltip = self._model.get_instrument_identification()
        self._view.set_instrument_display(model_name, tooltip)

    def _update_view_for_state(self, state: EquipmentState) -> None:
        """Update view based on current state."""
        state_name = state.name

        self._view.set_state_display(state_name)
        self._view.set_buttons_for_state(state_name)

        # Update connection indicator
        connected = state in (
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        )
        self._view.set_connection_status(connected)

        # Check if run should be enabled (need both connection and test plan)
        if state == EquipmentState.IDLE and self._model.test_plan is None:
            # Can't run without a test plan, but leave button state for visual feedback
            pass

        # Update "Start from" button based on selection and state
        if state in (EquipmentState.IDLE, EquipmentState.PAUSED):
            selected = self._view.get_active_table_selected_step()
            has_plan = self._model.test_plan is not None
            self._view.set_start_from_enabled(selected is not None and has_plan)

    # Runtime timer methods

    def _start_runtime_timer(self) -> None:
        """Start the runtime timer that updates every second."""
        self._update_runtime()

    def _update_runtime(self) -> None:
        """Update runtime display and schedule next update."""
        if self._run_start_time is not None and self._model.test_plan is not None:
            elapsed = time.time() - self._run_start_time
            total = (
                self._partial_total_duration
                or self._model.test_plan.total_duration
            )
            remaining = max(0.0, total - elapsed)
            self._view.set_runtime_display(int(elapsed))
            self._view.set_remaining_time_display(remaining)
            self._runtime_timer_id = self._view.schedule(1000, self._update_runtime)

    def _stop_runtime_timer(self) -> None:
        """Stop the runtime timer and reset display."""
        if self._runtime_timer_id is not None:
            self._view.cancel_schedule(self._runtime_timer_id)
            self._runtime_timer_id = None
        self._run_start_time = None
        self._partial_total_duration = None
        self._view.set_runtime_display(None)
        # Show total duration if a plan is loaded, otherwise --:--
        if self._model.test_plan is not None:
            self._view.set_remaining_time_display(self._model.test_plan.total_duration)
        else:
            self._view.set_remaining_time_display(None)

    def _stop_runtime_timer_for_pause(self) -> None:
        """Stop the runtime timer but preserve display values for pause."""
        if self._runtime_timer_id is not None:
            self._view.cancel_schedule(self._runtime_timer_id)
            self._runtime_timer_id = None
        # Don't reset run_start_time or displays - keep showing paused values

    def shutdown(self) -> None:
        """Clean shutdown of presenter."""
        logger.info("EquipmentPresenter shutting down")
        self._stop_runtime_timer()
        self._task_runner.stop()

        # Disconnect if connected
        if self._model.state in (
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        ):
            try:
                self._model.disconnect()
            except Exception as e:
                logger.warning("Error during disconnect on shutdown: %s", e)
