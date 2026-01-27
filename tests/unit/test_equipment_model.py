"""Tests for the equipment model module."""

from unittest.mock import Mock, patch

import pytest

from visa_vulture.model.equipment import EquipmentModel
from visa_vulture.model.state_machine import EquipmentState
from visa_vulture.model.test_plan import (
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    TestPlan,
)


class TestEquipmentModelInitialization:
    """Tests for EquipmentModel initialization."""

    def test_initial_state_is_unknown(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Initial state should be UNKNOWN."""
        assert equipment_model.state == EquipmentState.UNKNOWN

    def test_no_instruments_initially(
        self, equipment_model: EquipmentModel
    ) -> None:
        """No instruments are configured initially."""
        assert equipment_model.instruments == {}

    def test_no_test_plan_initially(
        self, equipment_model: EquipmentModel
    ) -> None:
        """No test plan is loaded initially."""
        assert equipment_model.test_plan is None


class TestEquipmentModelCallbacks:
    """Tests for callback registration."""

    def test_register_state_callback(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """State callback is registered and called on state change."""
        callback_calls = []

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            callback_calls.append((old, new))

        equipment_model.register_state_callback(callback)
        equipment_model.connect()  # Triggers UNKNOWN -> IDLE

        assert len(callback_calls) == 1
        assert callback_calls[0] == (EquipmentState.UNKNOWN, EquipmentState.IDLE)

    def test_register_progress_callback(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Progress callback can be registered."""
        callback = Mock()
        equipment_model.register_progress_callback(callback)

        # Callback is stored (we can't easily verify without running a test)
        assert callback in equipment_model._progress_callbacks

    def test_register_complete_callback(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Complete callback can be registered."""
        callback = Mock()
        equipment_model.register_complete_callback(callback)

        assert callback in equipment_model._complete_callbacks


class TestEquipmentModelInstruments:
    """Tests for instrument management."""

    def test_add_power_supply_instrument(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Power supply instrument can be added."""
        equipment_model.add_instrument(
            name="PS1",
            resource_address="TCPIP::192.168.1.100::INSTR",
            instrument_type="power_supply",
        )

        assert "PS1" in equipment_model.instruments
        assert equipment_model.instruments["PS1"].name == "PS1"

    def test_add_signal_generator_instrument(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Signal generator instrument can be added."""
        equipment_model.add_instrument(
            name="SG1",
            resource_address="TCPIP::192.168.1.101::INSTR",
            instrument_type="signal_generator",
        )

        assert "SG1" in equipment_model.instruments

    def test_add_unknown_instrument_type_raises(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Unknown instrument type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown instrument type"):
            equipment_model.add_instrument(
                name="Scope",
                resource_address="TCPIP::192.168.1.102::INSTR",
                instrument_type="oscilloscope",
            )

    def test_instruments_property(
        self, equipment_model: EquipmentModel
    ) -> None:
        """instruments property returns all added instruments."""
        equipment_model.add_instrument(
            name="PS1",
            resource_address="TCPIP::192.168.1.100::INSTR",
            instrument_type="power_supply",
        )
        equipment_model.add_instrument(
            name="SG1",
            resource_address="TCPIP::192.168.1.101::INSTR",
            instrument_type="signal_generator",
        )

        instruments = equipment_model.instruments
        assert len(instruments) == 2
        assert "PS1" in instruments
        assert "SG1" in instruments


class TestEquipmentModelTestPlan:
    """Tests for test plan loading."""

    def test_load_valid_test_plan(
        self, equipment_model: EquipmentModel, sample_power_supply_plan: TestPlan
    ) -> None:
        """Valid test plan is loaded successfully."""
        equipment_model.load_test_plan(sample_power_supply_plan)

        assert equipment_model.test_plan is sample_power_supply_plan

    def test_load_invalid_test_plan_raises(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Invalid test plan raises ValueError."""
        invalid_plan = TestPlan(
            name="",  # Empty name is invalid
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[PowerSupplyTestStep(step_number=1, duration_seconds=1.0)],
        )

        with pytest.raises(ValueError, match="Invalid test plan"):
            equipment_model.load_test_plan(invalid_plan)

    def test_test_plan_property(
        self, equipment_model: EquipmentModel, sample_power_supply_plan: TestPlan
    ) -> None:
        """test_plan property returns loaded plan."""
        equipment_model.load_test_plan(sample_power_supply_plan)
        assert equipment_model.test_plan is sample_power_supply_plan


class TestEquipmentModelConnect:
    """Tests for connect method."""

    def test_connect_opens_visa_if_needed(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """connect opens VISA connection if not already open."""
        mock_visa_connection.is_open = False
        equipment_model.connect()

        mock_visa_connection.open.assert_called_once()

    def test_connect_transitions_to_idle(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Successful connect transitions to IDLE state."""
        equipment_model.connect()

        assert equipment_model.state == EquipmentState.IDLE

    def test_connect_from_error_state_allowed(
        self, mock_visa_connection: Mock
    ) -> None:
        """Connect is allowed from ERROR state."""
        model = EquipmentModel(mock_visa_connection)
        # Manually set to ERROR state
        model._state_machine._state = EquipmentState.ERROR

        model.connect()

        assert model.state == EquipmentState.IDLE

    def test_connect_from_idle_state_raises(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Connect from IDLE state raises RuntimeError."""
        equipment_model.connect()  # Now in IDLE

        with pytest.raises(RuntimeError, match="Cannot connect"):
            equipment_model.connect()

    def test_connect_from_running_state_raises(
        self, mock_visa_connection: Mock
    ) -> None:
        """Connect from RUNNING state raises RuntimeError."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.RUNNING

        with pytest.raises(RuntimeError, match="Cannot connect"):
            model.connect()

    def test_connect_failure_transitions_to_error(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Connection failure transitions to ERROR state."""
        mock_visa_connection.open.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            equipment_model.connect()

        assert equipment_model.state == EquipmentState.ERROR

    def test_connect_connects_all_instruments(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """connect calls connect on all instruments."""
        equipment_model.add_instrument(
            name="PS1",
            resource_address="TCPIP::192.168.1.100::INSTR",
            instrument_type="power_supply",
        )

        equipment_model.connect()

        # Instrument should have connect called (via open_resource)
        mock_visa_connection.open_resource.assert_called()


class TestEquipmentModelDisconnect:
    """Tests for disconnect method."""

    def test_disconnect_resets_state(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Disconnect resets state to UNKNOWN."""
        equipment_model.connect()
        assert equipment_model.state == EquipmentState.IDLE

        equipment_model.disconnect()

        assert equipment_model.state == EquipmentState.UNKNOWN

    def test_disconnect_closes_visa(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Disconnect closes VISA connection."""
        equipment_model.connect()
        equipment_model.disconnect()

        mock_visa_connection.close.assert_called()


class TestEquipmentModelRunTest:
    """Tests for run_test method."""

    def test_run_without_plan_raises(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Running without loaded plan raises RuntimeError."""
        equipment_model.connect()

        with pytest.raises(RuntimeError, match="No test plan loaded"):
            equipment_model.run_test()

    def test_run_from_unknown_state_raises(
        self, equipment_model: EquipmentModel, sample_power_supply_plan: TestPlan
    ) -> None:
        """Running from UNKNOWN state raises RuntimeError."""
        equipment_model.load_test_plan(sample_power_supply_plan)

        with pytest.raises(RuntimeError, match="Cannot run test"):
            equipment_model.run_test()

    def test_run_from_running_state_raises(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Running from RUNNING state raises RuntimeError."""
        model = EquipmentModel(mock_visa_connection)
        model.load_test_plan(sample_power_supply_plan)
        model._state_machine._state = EquipmentState.RUNNING

        with pytest.raises(RuntimeError, match="Cannot run test"):
            model.run_test()


class TestEquipmentModelStopTest:
    """Tests for stop_test method."""

    def test_stop_sets_flag(
        self, mock_visa_connection: Mock
    ) -> None:
        """stop_test sets the stop flag when running."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.RUNNING

        model.stop_test()

        assert model._stop_requested is True

    def test_stop_only_when_running_or_paused(
        self, equipment_model: EquipmentModel
    ) -> None:
        """stop_test only sets flag when in RUNNING or PAUSED state."""
        equipment_model.stop_test()

        assert equipment_model._stop_requested is False

    def test_stop_from_paused_sets_flag(
        self, mock_visa_connection: Mock
    ) -> None:
        """stop_test sets stop flag and clears pause flag when paused."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.PAUSED
        model._pause_requested = True

        model.stop_test()

        assert model._stop_requested is True
        assert model._pause_requested is False

    def test_stop_from_paused_transitions_to_idle(
        self, mock_visa_connection: Mock, sample_power_supply_plan
    ) -> None:
        """Stopping from PAUSED state transitions to IDLE (regression test).

        This tests the run_test() finally block: when a test is paused and stop
        is requested, the finally block must transition to IDLE.
        Previously, it only checked for RUNNING state and missed PAUSED.
        """
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.IDLE
        model._test_plan = sample_power_supply_plan

        # Track state transitions
        state_changes: list[tuple[EquipmentState, EquipmentState]] = []

        def track_state(old: EquipmentState, new: EquipmentState) -> None:
            state_changes.append((old, new))

        model.register_state_callback(track_state)

        # Mock _execute_power_supply_plan to simulate pause then stop
        def mock_execute() -> None:
            # Simulate: start running, pause, then stop
            model._pause_requested = True
            model._state_machine.to_paused()
            # Now simulate stop while paused
            model._stop_requested = True
            model._pause_requested = False
            # Method returns, run_test's finally block should handle transition

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            model.run_test()

        # The final state should be IDLE, not stuck at PAUSED
        assert model.state == EquipmentState.IDLE

        # Verify we went through the expected state transitions
        # IDLE -> RUNNING -> PAUSED -> IDLE
        assert (EquipmentState.IDLE, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.PAUSED) in state_changes
        assert (EquipmentState.PAUSED, EquipmentState.IDLE) in state_changes


class TestEquipmentModelPauseTest:
    """Tests for pause_test method."""

    def test_pause_sets_flag_when_running(
        self, mock_visa_connection: Mock
    ) -> None:
        """pause_test sets the pause flag when running."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.RUNNING

        model.pause_test()

        assert model._pause_requested is True

    def test_pause_only_when_running(
        self, equipment_model: EquipmentModel
    ) -> None:
        """pause_test only sets flag when in RUNNING state."""
        equipment_model.pause_test()

        assert equipment_model._pause_requested is False

    def test_pause_from_idle_does_nothing(
        self, mock_visa_connection: Mock
    ) -> None:
        """pause_test does nothing when in IDLE state."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.IDLE

        model.pause_test()

        assert model._pause_requested is False


class TestEquipmentModelResumeTest:
    """Tests for resume_test method."""

    def test_resume_clears_pause_flag(
        self, mock_visa_connection: Mock
    ) -> None:
        """resume_test clears the pause flag when paused."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.PAUSED
        model._pause_requested = True

        model.resume_test()

        assert model._pause_requested is False

    def test_resume_only_when_paused(
        self, mock_visa_connection: Mock
    ) -> None:
        """resume_test only clears flag when in PAUSED state."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.RUNNING
        model._pause_requested = True

        model.resume_test()

        # Flag should still be set since we're not in PAUSED state
        assert model._pause_requested is True


class TestEquipmentModelRunTestExecution:
    """Integration tests for run_test() execution paths and state transitions.

    These tests verify that run_test() correctly transitions through states
    during actual execution, using mocked _execute_*_plan() methods to control
    the execution flow without requiring real instruments.
    """

    def _make_model_at_idle(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> EquipmentModel:
        """Create a model in IDLE state with a loaded test plan."""
        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.IDLE
        model._test_plan = sample_power_supply_plan
        return model

    def _track_state_changes(
        self, model: EquipmentModel
    ) -> list[tuple[EquipmentState, EquipmentState]]:
        """Register a callback that records state transitions."""
        changes: list[tuple[EquipmentState, EquipmentState]] = []

        def track(old: EquipmentState, new: EquipmentState) -> None:
            changes.append((old, new))

        model.register_state_callback(track)
        return changes

    def test_successful_execution_transitions(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Successful test run transitions IDLE → RUNNING → IDLE."""
        model = self._make_model_at_idle(
            mock_visa_connection, sample_power_supply_plan
        )
        state_changes = self._track_state_changes(model)

        complete_results: list[tuple[bool, str]] = []
        model.register_complete_callback(
            lambda success, msg: complete_results.append((success, msg))
        )

        def mock_execute() -> None:
            # Simulate successful execution (no exceptions, no stop)
            pass

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            model.run_test()

        assert model.state == EquipmentState.IDLE
        assert (EquipmentState.IDLE, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.IDLE) in state_changes
        assert len(complete_results) == 1
        assert complete_results[0][0] is True

    def test_exception_during_execution_transitions_to_error(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Exception during execution transitions IDLE → RUNNING → ERROR."""
        model = self._make_model_at_idle(
            mock_visa_connection, sample_power_supply_plan
        )
        state_changes = self._track_state_changes(model)

        complete_results: list[tuple[bool, str]] = []
        model.register_complete_callback(
            lambda success, msg: complete_results.append((success, msg))
        )

        def mock_execute() -> None:
            raise RuntimeError("Instrument communication error")

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            with pytest.raises(RuntimeError, match="Instrument communication error"):
                model.run_test()

        assert model.state == EquipmentState.ERROR
        assert (EquipmentState.IDLE, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.ERROR) in state_changes
        # Finally block should NOT also transition (already in ERROR)
        assert (EquipmentState.ERROR, EquipmentState.IDLE) not in state_changes
        assert len(complete_results) == 1
        assert complete_results[0][0] is False

    def test_stop_while_running_transitions_to_idle(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Stop during execution transitions IDLE → RUNNING → IDLE."""
        model = self._make_model_at_idle(
            mock_visa_connection, sample_power_supply_plan
        )
        state_changes = self._track_state_changes(model)

        complete_results: list[tuple[bool, str]] = []
        model.register_complete_callback(
            lambda success, msg: complete_results.append((success, msg))
        )

        def mock_execute() -> None:
            # Simulate stop requested during execution
            model._stop_requested = True

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            model.run_test()

        assert model.state == EquipmentState.IDLE
        assert (EquipmentState.IDLE, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.IDLE) in state_changes
        assert len(complete_results) == 1
        assert complete_results[0][0] is False  # Stopped, not successful

    def test_pause_transitions_to_paused(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Pause during execution transitions RUNNING → PAUSED, then stop resumes to IDLE."""
        model = self._make_model_at_idle(
            mock_visa_connection, sample_power_supply_plan
        )
        state_changes = self._track_state_changes(model)

        def mock_execute() -> None:
            # Simulate: pause, then stop (to exit)
            model._pause_requested = True
            model._state_machine.to_paused()
            # Then stop to let run_test() finish
            model._stop_requested = True
            model._pause_requested = False

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            model.run_test()

        assert model.state == EquipmentState.IDLE
        assert (EquipmentState.IDLE, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.PAUSED) in state_changes
        assert (EquipmentState.PAUSED, EquipmentState.IDLE) in state_changes

    def test_resume_from_paused_continues_execution(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Resume after pause transitions PAUSED → RUNNING → IDLE."""
        model = self._make_model_at_idle(
            mock_visa_connection, sample_power_supply_plan
        )
        state_changes = self._track_state_changes(model)

        complete_results: list[tuple[bool, str]] = []
        model.register_complete_callback(
            lambda success, msg: complete_results.append((success, msg))
        )

        def mock_execute() -> None:
            # Simulate: pause, then resume, then complete
            model._pause_requested = True
            model._state_machine.to_paused()
            # Resume
            model._pause_requested = False
            model._state_machine.to_running()

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            model.run_test()

        assert model.state == EquipmentState.IDLE
        assert (EquipmentState.IDLE, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.PAUSED) in state_changes
        assert (EquipmentState.PAUSED, EquipmentState.RUNNING) in state_changes
        assert (EquipmentState.RUNNING, EquipmentState.IDLE) in state_changes
        # Completed successfully after resume
        assert len(complete_results) == 1
        assert complete_results[0][0] is True

    def test_exception_while_paused_transitions_to_error(
        self, mock_visa_connection: Mock, sample_power_supply_plan: TestPlan
    ) -> None:
        """Exception while paused transitions PAUSED → ERROR."""
        model = self._make_model_at_idle(
            mock_visa_connection, sample_power_supply_plan
        )
        state_changes = self._track_state_changes(model)

        complete_results: list[tuple[bool, str]] = []
        model.register_complete_callback(
            lambda success, msg: complete_results.append((success, msg))
        )

        def mock_execute() -> None:
            # Simulate: pause, then error
            model._pause_requested = True
            model._state_machine.to_paused()
            raise RuntimeError("Instrument lost connection")

        with patch.object(model, "_execute_power_supply_plan", mock_execute):
            with pytest.raises(RuntimeError, match="Instrument lost connection"):
                model.run_test()

        assert model.state == EquipmentState.ERROR
        assert (EquipmentState.RUNNING, EquipmentState.PAUSED) in state_changes
        assert (EquipmentState.PAUSED, EquipmentState.ERROR) in state_changes
        # Finally block should NOT also transition (already in ERROR)
        assert (EquipmentState.ERROR, EquipmentState.IDLE) not in state_changes
        assert len(complete_results) == 1
        assert complete_results[0][0] is False


class TestEquipmentModelIdentification:
    """Tests for get_instrument_identification method."""

    def test_get_instrument_identification_not_found(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Returns (None, None) when no matching instrument."""
        model_name, formatted_id = equipment_model.get_instrument_identification(
            "power_supply"
        )

        assert model_name is None
        assert formatted_id is None

    def test_get_instrument_identification_not_connected(
        self, equipment_model: EquipmentModel
    ) -> None:
        """Returns (None, None) when instrument not connected."""
        equipment_model.add_instrument(
            name="PS1",
            resource_address="TCPIP::192.168.1.100::INSTR",
            instrument_type="power_supply",
        )

        model_name, formatted_id = equipment_model.get_instrument_identification(
            "power_supply"
        )

        assert model_name is None
        assert formatted_id is None


class TestEquipmentModelScanResources:
    """Tests for scan_resources method."""

    def test_scan_resources_opens_visa_if_needed(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """scan_resources opens VISA if not already open."""
        mock_visa_connection.is_open = False

        equipment_model.scan_resources()

        mock_visa_connection.open.assert_called_once()

    def test_scan_resources_returns_list(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """scan_resources returns list of resource addresses."""
        mock_visa_connection.list_resources.return_value = (
            "TCPIP::192.168.1.100::INSTR",
            "TCPIP::192.168.1.101::INSTR",
        )

        resources = equipment_model.scan_resources()

        assert isinstance(resources, list)
        assert len(resources) == 2


class TestRunTestFromStep:
    """Tests for run_test_from_step method."""

    def test_no_plan_raises(
        self, equipment_model: EquipmentModel, mock_visa_connection: Mock
    ) -> None:
        """Running from step without plan raises RuntimeError."""
        equipment_model.connect()
        with pytest.raises(RuntimeError, match="No test plan loaded"):
            equipment_model.run_test_from_step(2)

    def test_invalid_step_raises(
        self,
        equipment_model: EquipmentModel,
        mock_visa_connection: Mock,
        sample_power_supply_plan: TestPlan,
    ) -> None:
        """Running from nonexistent step raises ValueError."""
        equipment_model.connect()
        equipment_model.load_test_plan(sample_power_supply_plan)
        with pytest.raises(ValueError, match="Step 99 not found"):
            equipment_model.run_test_from_step(99)

    def test_wrong_state_raises(
        self,
        equipment_model: EquipmentModel,
        sample_power_supply_plan: TestPlan,
    ) -> None:
        """Running from step in UNKNOWN state raises RuntimeError."""
        # Don't connect - stays in UNKNOWN
        equipment_model.load_test_plan(sample_power_supply_plan)
        with pytest.raises(RuntimeError, match="Cannot run test"):
            equipment_model.run_test_from_step(1)

    def test_skips_earlier_steps(self, mock_visa_connection: Mock) -> None:
        """_execute_power_supply_plan with start_step=2 skips step 1."""
        from visa_vulture.instruments import PowerSupply

        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.RUNNING
        model._test_plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(
                    step_number=1, duration_seconds=0.0, voltage=5.0, current=1.0
                ),
                PowerSupplyTestStep(
                    step_number=2, duration_seconds=0.0, voltage=10.0, current=2.0
                ),
                PowerSupplyTestStep(
                    step_number=3, duration_seconds=0.0, voltage=15.0, current=3.0
                ),
            ],
        )

        mock_ps = Mock(spec=PowerSupply)
        mock_ps.is_connected = True
        model._instruments = {"ps": mock_ps}

        progress_steps: list[int] = []
        model.register_progress_callback(
            lambda current, total, step: progress_steps.append(step.step_number)
        )

        model._execute_power_supply_plan(start_step=2)

        assert progress_steps == [2, 3]
        mock_ps.enable_output.assert_called_once()

    def test_enables_output_on_start_step(self, mock_visa_connection: Mock) -> None:
        """Output is enabled on the start step, not step 1."""
        from visa_vulture.instruments import PowerSupply

        model = EquipmentModel(mock_visa_connection)
        model._state_machine._state = EquipmentState.RUNNING
        model._test_plan = TestPlan(
            name="Test",
            plan_type=PLAN_TYPE_POWER_SUPPLY,
            steps=[
                PowerSupplyTestStep(
                    step_number=1, duration_seconds=0.0, voltage=5.0, current=1.0
                ),
                PowerSupplyTestStep(
                    step_number=2, duration_seconds=0.0, voltage=10.0, current=2.0
                ),
            ],
        )

        mock_ps = Mock(spec=PowerSupply)
        mock_ps.is_connected = True
        model._instruments = {"ps": mock_ps}

        model._execute_power_supply_plan(start_step=2)

        # enable_output should have been called exactly once (on step 2, not step 1)
        mock_ps.enable_output.assert_called_once()
