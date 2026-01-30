"""Equipment model - core business logic."""

import logging
import time
from typing import Callable

from ..instruments import BaseInstrument, PowerSupply, SignalGenerator, VISAConnection
from .state_machine import EquipmentState, StateMachine
from .test_plan import (
    TestPlan,
    TestStep,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
)

logger = logging.getLogger(__name__)

# Type aliases
TestProgressCallback = Callable[[int, int, TestStep], None]
TestCompleteCallback = Callable[[bool, str], None]


class EquipmentModel:
    """
    Core business logic for equipment control.

    Manages instruments, state machine, and test execution.
    Does not know about the GUI.
    """

    def __init__(self, visa_connection: VISAConnection):
        """
        Initialize equipment model.

        Args:
            visa_connection: VISA connection manager
        """
        self._visa = visa_connection
        self._state_machine = StateMachine()
        self._instrument: BaseInstrument | None = None
        self._instrument_type: str | None = None
        self._test_plan: TestPlan | None = None
        self._stop_requested = False
        self._pause_requested = False
        self._time_remaining_in_step: float | None = None

        # Callbacks for test execution
        self._progress_callbacks: list[TestProgressCallback] = []
        self._complete_callbacks: list[TestCompleteCallback] = []

    @property
    def state(self) -> EquipmentState:
        """Get current equipment state."""
        return self._state_machine.state

    @property
    def test_plan(self) -> TestPlan | None:
        """Get loaded test plan."""
        return self._test_plan

    @property
    def instrument(self) -> BaseInstrument | None:
        """Get the connected instrument."""
        return self._instrument

    @property
    def instrument_type(self) -> str | None:
        """Get the type of connected instrument."""
        return self._instrument_type

    def register_state_callback(
        self, callback: Callable[[EquipmentState, EquipmentState], None]
    ) -> None:
        """Register callback for state changes."""
        self._state_machine.register_callback(callback)

    def register_progress_callback(self, callback: TestProgressCallback) -> None:
        """Register callback for test progress updates."""
        self._progress_callbacks.append(callback)

    def register_complete_callback(self, callback: TestCompleteCallback) -> None:
        """Register callback for test completion."""
        self._complete_callbacks.append(callback)

    def scan_resources(self) -> list[str]:
        """
        Scan for available VISA resources.

        Returns:
            List of resource address strings
        """
        if not self._visa.is_open:
            self._visa.open()
        return list(self._visa.list_resources())

    def get_instrument_identification(self) -> tuple[str | None, str | None]:
        """
        Get model name and formatted identification for the connected instrument.

        Returns:
            Tuple of (model_name, formatted_identification) or (None, None) if not connected
        """
        if (
            self._instrument
            and self._instrument.is_connected
            and self._instrument.identification
        ):
            return self._instrument.model(), self._instrument.formatted_identification()
        return None, None

    def identify_resource(
        self, resource_address: str, timeout_ms: int = 2000
    ) -> str | None:
        """
        Temporarily open a resource, query *IDN?, and close it.

        Used by Resource Manager dialog to identify instruments before connecting.

        Args:
            resource_address: VISA resource address string
            timeout_ms: Timeout for identification query

        Returns:
            Identification string, or None if query failed
        """
        if not self._visa.is_open:
            self._visa.open()

        try:
            resource = self._visa.open_resource(resource_address, timeout_ms)
            try:
                return resource.query("*IDN?").strip()
            finally:
                resource.close()
        except Exception as e:
            logger.warning("Failed to identify %s: %s", resource_address, e)
            return None

    def connect_instrument(
        self,
        resource_address: str,
        instrument_type: str,
        timeout_ms: int = 5000,
    ) -> None:
        """
        Connect to a single instrument.

        Creates the appropriate instrument class and connects it.

        Args:
            resource_address: VISA resource address string
            instrument_type: Type string ("power_supply" or "signal_generator")
            timeout_ms: Communication timeout in milliseconds

        Raises:
            RuntimeError: If not in valid state for connection
            ValueError: If instrument_type is unknown
        """
        if self._state_machine.state not in (
            EquipmentState.UNKNOWN,
            EquipmentState.ERROR,
        ):
            raise RuntimeError(
                f"Cannot connect in {self._state_machine.state.name} state"
            )

        try:
            if not self._visa.is_open:
                self._visa.open()

            # Create appropriate instrument class
            if instrument_type == "power_supply":
                self._instrument = PowerSupply(
                    "Power Supply", resource_address, timeout_ms
                )
            elif instrument_type == "signal_generator":
                self._instrument = SignalGenerator(
                    "Signal Generator", resource_address, timeout_ms
                )
            else:
                raise ValueError(f"Unknown instrument type: {instrument_type}")

            self._instrument_type = instrument_type

            # Connect to the instrument
            resource = self._visa.open_resource(
                resource_address,
                timeout_ms,
                self._instrument._read_termination,
                self._instrument._write_termination,
            )
            self._instrument.connect(resource)

            self._state_machine.to_idle()
            logger.info(
                "Connected to %s at %s", instrument_type, resource_address
            )

        except Exception as e:
            logger.error("Connection failed: %s", e)
            self._instrument = None
            self._instrument_type = None
            self._state_machine.to_error(str(e))
            raise

    def disconnect(self) -> None:
        """Disconnect from the instrument."""
        if self._instrument is not None and self._instrument.is_connected:
            self._instrument.disconnect()
            logger.info("Instrument disconnected")
        else:
            logger.info("No connected instrument to disconnect")

        self._instrument = None
        self._instrument_type = None
        self._state_machine.reset()
        self._visa.close()

    def load_test_plan(self, test_plan: TestPlan) -> None:
        """
        Load a test plan.

        Args:
            test_plan: TestPlan to load

        Raises:
            ValueError: If test plan is invalid
        """
        errors = test_plan.validate()
        if errors:
            raise ValueError(f"Invalid test plan: {'; '.join(errors)}")

        self._test_plan = test_plan
        logger.info("Loaded test plan: %s", test_plan)

    def run_test(self) -> None:
        """
        Execute the loaded test plan.

        Must be called from a background thread.
        Transitions through RUNNING state and back to IDLE on completion.
        """
        if self._test_plan is None:
            raise RuntimeError("No test plan loaded")

        if self._state_machine.state != EquipmentState.IDLE:
            raise RuntimeError(
                f"Cannot run test in {self._state_machine.state.name} state"
            )

        self._stop_requested = False
        self._pause_requested = False
        self._state_machine.to_running()

        try:
            # Dispatch based on plan type
            if self._test_plan.plan_type == PLAN_TYPE_POWER_SUPPLY:
                self._execute_power_supply_plan()
            elif self._test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                self._execute_signal_generator_plan()
            else:
                raise RuntimeError(f"Unknown plan type: {self._test_plan.plan_type}")

            success = not self._stop_requested
            message = "Test completed" if success else "Test stopped by user"
        except Exception as e:
            logger.error("Test execution failed: %s", e)
            self._state_machine.to_error(str(e))
            self._notify_complete(False, str(e))
            raise
        finally:
            if self._state_machine.state in (
                EquipmentState.RUNNING,
                EquipmentState.PAUSED,
            ):
                self._state_machine.to_idle()

        self._notify_complete(success, message)

    def run_test_from_step(self, start_step: int) -> None:
        """
        Execute the loaded test plan starting from a specific step.

        Must be called from a background thread.
        Transitions through RUNNING state and back to IDLE on completion.

        Args:
            start_step: 1-based step number to start execution from.
                        Output is always enabled on the first executed step.
        """
        if self._test_plan is None:
            raise RuntimeError("No test plan loaded")

        if self._state_machine.state != EquipmentState.IDLE:
            raise RuntimeError(
                f"Cannot run test in {self._state_machine.state.name} state"
            )

        if self._test_plan.get_step(start_step) is None:
            raise ValueError(f"Step {start_step} not found in test plan")

        self._stop_requested = False
        self._pause_requested = False
        self._state_machine.to_running()

        try:
            if self._test_plan.plan_type == PLAN_TYPE_POWER_SUPPLY:
                self._execute_power_supply_plan(start_step=start_step)
            elif self._test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                self._execute_signal_generator_plan(start_step=start_step)
            else:
                raise RuntimeError(f"Unknown plan type: {self._test_plan.plan_type}")

            success = not self._stop_requested
            message = "Test completed" if success else "Test stopped by user"
        except Exception as e:
            logger.error("Test execution failed: %s", e)
            self._state_machine.to_error(str(e))
            self._notify_complete(False, str(e))
            raise
        finally:
            if self._state_machine.state in (
                EquipmentState.RUNNING,
                EquipmentState.PAUSED,
            ):
                self._state_machine.to_idle()

        self._notify_complete(success, message)

    def stop_test(self) -> None:
        """Request test execution to stop."""
        if self._state_machine.state in (
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        ):
            logger.info("Stop requested")
            self._stop_requested = True
            self._pause_requested = False  # Clear pause flag so loop can exit

    def pause_test(self) -> None:
        """Request test execution to pause."""
        if self._state_machine.state == EquipmentState.RUNNING:
            logger.info("Pause requested")
            self._pause_requested = True

    def resume_test(self) -> None:
        """Request test execution to resume."""
        if self._state_machine.state == EquipmentState.PAUSED:
            logger.info("Resume requested")
            self._pause_requested = False

    def _execute_power_supply_plan(self, start_step: int = 1) -> None:
        """Execute power supply test plan steps.

        Args:
            start_step: 1-based step number to start from (default: 1)
        """
        if (
            self._test_plan is None
            or self._test_plan.plan_type != PLAN_TYPE_POWER_SUPPLY
        ):
            return

        # Get the power supply
        if not isinstance(self._instrument, PowerSupply):
            raise RuntimeError("Connected instrument is not a power supply")
        power_supply = self._instrument

        total_steps = self._test_plan.step_count
        sorted_steps = sorted(self._test_plan.steps, key=lambda s: s.step_number)

        for step in sorted_steps:
            # Skip steps before start_step
            if step.step_number < start_step:
                continue

            if self._stop_requested:
                logger.info("Test stopped at step %d", step.step_number)
                break

            # Type narrow: steps in power supply plan must be PowerSupplyTestStep
            if not isinstance(step, PowerSupplyTestStep):
                raise TypeError(f"Expected PowerSupplyTestStep, got {type(step)}")

            logger.info(
                "Executing step %d/%d: V=%.3f, I=%.3f",
                step.step_number,
                total_steps,
                step.voltage,
                step.current,
            )

            # Apply settings
            power_supply.set_voltage(step.voltage)
            power_supply.set_current(step.current)

            # Enable output on first executed step
            if step.step_number == start_step:
                power_supply.enable_output()

            # Notify progress
            self._notify_progress(step.step_number, total_steps, step)

            # Wait for step duration
            if step.duration_seconds > 0:
                self._interruptible_sleep(step.duration_seconds)

        # Disable output at end
        if power_supply.is_connected:
            power_supply.disable_output()

    def _execute_signal_generator_plan(self, start_step: int = 1) -> None:
        """Execute signal generator test plan steps.

        Args:
            start_step: 1-based step number to start from (default: 1)
        """
        if (
            self._test_plan is None
            or self._test_plan.plan_type != PLAN_TYPE_SIGNAL_GENERATOR
        ):
            return

        # Get the signal generator
        if not isinstance(self._instrument, SignalGenerator):
            raise RuntimeError("Connected instrument is not a signal generator")
        signal_gen = self._instrument

        total_steps = self._test_plan.step_count
        sorted_steps = sorted(self._test_plan.steps, key=lambda s: s.step_number)

        for step in sorted_steps:
            # Skip steps before start_step
            if step.step_number < start_step:
                continue

            if self._stop_requested:
                logger.info("Test stopped at step %d", step.step_number)
                break

            # Type narrow: steps in signal generator plan must be SignalGeneratorTestStep
            if not isinstance(step, SignalGeneratorTestStep):
                raise TypeError(f"Expected SignalGeneratorTestStep, got {type(step)}")

            logger.info(
                "Executing step %d/%d: F=%.1f Hz, P=%.2f dBm",
                step.step_number,
                total_steps,
                step.frequency,
                step.power,
            )

            # Apply settings
            signal_gen.set_frequency(step.frequency)
            signal_gen.set_power(step.power)

            # Enable output on first executed step
            if step.step_number == start_step:
                signal_gen.enable_output()

            # Notify progress
            self._notify_progress(step.step_number, total_steps, step)

            # Wait for step duration
            if step.duration_seconds > 0:
                self._interruptible_sleep(step.duration_seconds)

        # Disable output at end
        if signal_gen.is_connected:
            signal_gen.disable_output()

    def _interruptible_sleep(self, duration: float) -> None:
        """Sleep that can be interrupted by stop or pause request."""
        remaining = duration

        while remaining > 0 and not self._stop_requested:
            if self._pause_requested:
                # Store remaining time for this step
                self._time_remaining_in_step = remaining

                # Transition to PAUSED state
                self._state_machine.to_paused()

                # Wait until resumed or stopped
                while self._pause_requested and not self._stop_requested:
                    time.sleep(0.1)

                if not self._stop_requested:
                    # Resumed - continue with remaining time
                    remaining = self._time_remaining_in_step or remaining
                    self._time_remaining_in_step = None
                    self._state_machine.to_running()
            else:
                # Normal sleep chunk
                sleep_chunk = min(0.1, remaining)
                time.sleep(sleep_chunk)
                remaining -= sleep_chunk

    def _notify_progress(self, current: int, total: int, step: TestStep) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(current, total, step)
            except Exception as e:
                logger.error("Error in progress callback: %s", e)

    def _notify_complete(self, success: bool, message: str) -> None:
        """Notify completion callbacks."""
        for callback in self._complete_callbacks:
            try:
                callback(success, message)
            except Exception as e:
                logger.error("Error in complete callback: %s", e)
