"""Tests for EquipmentPresenter."""

import time
from unittest.mock import Mock

import pytest

from visa_vulture.model import (
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    EquipmentState,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    TestPlan,
)
from visa_vulture.presenter import EquipmentPresenter

from .presenter_test_helpers import (
    execute_scheduled_callbacks,
    set_model_state,
    trigger_complete,
    trigger_progress,
    trigger_state_change,
    trigger_view_callback,
)


class TestPresenterInitialization:
    """Tests for presenter initialization and wiring."""

    def test_wires_view_callbacks(
        self, presenter: EquipmentPresenter, mock_view: Mock
    ) -> None:
        """Presenter registers callbacks on view for user actions."""
        assert mock_view._callbacks["on_connect"] is not None
        assert mock_view._callbacks["on_disconnect"] is not None
        assert mock_view._callbacks["on_load_test_plan"] is not None
        assert mock_view._callbacks["on_run"] is not None
        assert mock_view._callbacks["on_stop"] is not None
        assert mock_view._callbacks["on_pause"] is not None

    def test_wires_model_callbacks(
        self, presenter: EquipmentPresenter, mock_model_for_presenter: Mock
    ) -> None:
        """Presenter registers callbacks on model for state/progress updates."""
        assert len(mock_model_for_presenter._state_callbacks) == 1
        assert len(mock_model_for_presenter._progress_callbacks) == 1
        assert len(mock_model_for_presenter._complete_callbacks) == 1

    @pytest.mark.skip(reason="Tab change event removed - single instrument shows only one tab")
    def test_binds_tab_change_event(
        self, presenter: EquipmentPresenter, mock_view: Mock
    ) -> None:
        """Presenter binds to notebook tab change event."""
        mock_view.plot_notebook.bind.assert_called_once()
        call_args = mock_view.plot_notebook.bind.call_args
        assert "<<NotebookTabChanged>>" in call_args[0]

    def test_initial_view_state_matches_model(
        self, presenter: EquipmentPresenter, mock_view: Mock
    ) -> None:
        """Initial view state reflects model's UNKNOWN state."""
        mock_view.set_state_display.assert_called_with("UNKNOWN")
        mock_view.set_buttons_for_state.assert_called_with("UNKNOWN")


class TestStateTransitionHandling:
    """Tests for state change callbacks and view updates."""

    def test_unknown_to_idle_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """State transition to IDLE updates displays and connection indicator."""
        trigger_state_change(
            mock_model_for_presenter, EquipmentState.UNKNOWN, EquipmentState.IDLE
        )
        execute_scheduled_callbacks(mock_view)

        mock_view.set_state_display.assert_called_with("IDLE")
        mock_view.set_buttons_for_state.assert_called_with("IDLE")
        mock_view.set_connection_status.assert_called_with(True)

    def test_idle_to_running_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """State transition to RUNNING updates displays."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        trigger_state_change(
            mock_model_for_presenter, EquipmentState.IDLE, EquipmentState.RUNNING
        )
        execute_scheduled_callbacks(mock_view)

        mock_view.set_state_display.assert_called_with("RUNNING")
        mock_view.set_buttons_for_state.assert_called_with("RUNNING")

    def test_running_to_paused_saves_elapsed(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Transitioning to PAUSED saves elapsed time."""
        # Setup: simulate running with timer
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)
        presenter._run_start_time = time.time() - 30.0  # 30 seconds elapsed
        presenter._runtime_timer_id = "timer_active"

        trigger_state_change(
            mock_model_for_presenter, EquipmentState.RUNNING, EquipmentState.PAUSED
        )
        execute_scheduled_callbacks(mock_view)

        # Elapsed time should be saved
        assert presenter._elapsed_at_pause is not None
        assert 29.0 <= presenter._elapsed_at_pause <= 31.0

    def test_running_to_idle_clears_timer(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Transitioning from RUNNING to IDLE clears timer state."""
        # Setup: simulate running with timer
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)
        presenter._run_start_time = time.time() - 10.0
        presenter._runtime_timer_id = "timer_active"

        trigger_state_change(
            mock_model_for_presenter, EquipmentState.RUNNING, EquipmentState.IDLE
        )
        execute_scheduled_callbacks(mock_view)

        # Timer state should be cleared
        assert presenter._run_start_time is None
        assert presenter._elapsed_at_pause is None

    def test_paused_to_idle_clears_pause_state(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Stop while paused clears elapsed_at_pause."""
        set_model_state(mock_model_for_presenter, EquipmentState.PAUSED)
        presenter._elapsed_at_pause = 45.0

        trigger_state_change(
            mock_model_for_presenter, EquipmentState.PAUSED, EquipmentState.IDLE
        )
        execute_scheduled_callbacks(mock_view)

        assert presenter._elapsed_at_pause is None

    def test_error_state_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Transition to ERROR state updates displays."""
        trigger_state_change(
            mock_model_for_presenter, EquipmentState.IDLE, EquipmentState.ERROR
        )
        execute_scheduled_callbacks(mock_view)

        mock_view.set_state_display.assert_called_with("ERROR")
        mock_view.set_buttons_for_state.assert_called_with("ERROR")
        mock_view.set_connection_status.assert_called_with(False)


@pytest.mark.skip(reason="Connect now opens ResourceManagerDialog - requires GUI testing")
class TestConnectHandler:
    """Tests for connect button handling.

    Note: These tests are skipped because the connect handler now opens a
    ResourceManagerDialog which requires a real Tkinter root window.
    The dialog-based connection flow is better tested through integration tests.
    """

    def test_connect_calls_model_connect(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Connect button triggers model.connect()."""
        trigger_view_callback(mock_view, "on_connect")

        mock_model_for_presenter.connect.assert_called_once()

    def test_connect_sets_connecting_status(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Connect button shows connecting status."""
        # Check status before connect completes
        mock_view.set_status.reset_mock()
        trigger_view_callback(mock_view, "on_connect")

        # First call should be "Connecting..."
        calls = mock_view.set_status.call_args_list
        assert any("Connecting" in str(call) for call in calls)

    def test_connect_success_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Successful connection updates connection status."""
        mock_model_for_presenter.connect.return_value = None

        trigger_view_callback(mock_view, "on_connect")

        mock_view.set_connection_status.assert_called_with(True)
        # Status should show "Connected"
        calls = mock_view.set_status.call_args_list
        assert any("Connected" in str(call) for call in calls)

    def test_connect_failure_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Connection failure shows error dialog."""
        mock_model_for_presenter.connect.side_effect = Exception("Connection refused")

        trigger_view_callback(mock_view, "on_connect")

        mock_view.show_error.assert_called_once()
        assert "Connection" in mock_view.show_error.call_args[0][0]

    def test_connect_updates_instrument_display(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Successful connection updates instrument display."""
        mock_model_for_presenter.connect.return_value = None
        mock_model_for_presenter.get_instrument_identification.return_value = (
            "Model123",
            "Mfg Model123 SN12345",
        )
        # Simulate state becoming IDLE after connect
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)

        trigger_view_callback(mock_view, "on_connect")

        mock_view.set_instrument_display.assert_called()


class TestDisconnectHandler:
    """Tests for disconnect button handling."""

    def test_disconnect_calls_model_disconnect(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Disconnect button triggers model.disconnect()."""
        trigger_view_callback(mock_view, "on_disconnect")

        mock_model_for_presenter.disconnect.assert_called_once()

    def test_disconnect_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Disconnect updates connection status and clears instrument display."""
        trigger_view_callback(mock_view, "on_disconnect")

        mock_view.set_connection_status.assert_called_with(False)
        mock_view.set_instrument_display.assert_called_with(None, None)


class TestLoadTestPlanHandler:
    """Tests for load test plan button handling."""

    def test_load_valid_power_supply_plan_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        test_plan_fixtures_path,
    ) -> None:
        """Loading valid power supply plan updates view correctly."""
        file_path = str(test_plan_fixtures_path / "valid_power_supply.csv")

        trigger_view_callback(mock_view, "on_load_test_plan", file_path)

        mock_model_for_presenter.load_test_plan.assert_called_once()
        mock_view.set_test_plan_name.assert_called()
        mock_view.show_power_supply_plot.assert_called_once()
        mock_view.power_supply_plot_panel.load_test_plan_preview.assert_called_once()
        mock_view.ps_table.load_steps.assert_called_once()

    def test_load_valid_signal_generator_plan_updates_view(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        test_plan_fixtures_path,
    ) -> None:
        """Loading valid signal generator plan switches to correct tab."""
        file_path = str(test_plan_fixtures_path / "valid_signal_generator.csv")

        trigger_view_callback(mock_view, "on_load_test_plan", file_path)

        mock_view.show_signal_generator_plot.assert_called_once()
        mock_view.signal_gen_plot_panel.load_test_plan_preview.assert_called_once()
        mock_view.sg_table.load_steps.assert_called_once()

    def test_load_invalid_plan_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        tmp_path,
    ) -> None:
        """Loading invalid plan shows error dialog."""
        # Create an invalid CSV file
        invalid_file = tmp_path / "invalid.csv"
        invalid_file.write_text("invalid,header,only\n")

        trigger_view_callback(mock_view, "on_load_test_plan", str(invalid_file))

        mock_view.show_error.assert_called()
        mock_model_for_presenter.load_test_plan.assert_not_called()

    def test_load_nonexistent_file_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        tmp_path,
    ) -> None:
        """Loading nonexistent file shows error dialog."""
        trigger_view_callback(
            mock_view, "on_load_test_plan", str(tmp_path / "nonexistent.csv")
        )

        mock_view.show_error.assert_called()

    def test_load_plan_sets_remaining_time(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        test_plan_fixtures_path,
    ) -> None:
        """Loading test plan sets remaining time display."""
        file_path = str(test_plan_fixtures_path / "valid_power_supply.csv")

        trigger_view_callback(mock_view, "on_load_test_plan", file_path)

        mock_view.set_remaining_time_display.assert_called()


class TestRunHandler:
    """Tests for run button handling."""

    def test_run_without_plan_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Run without loaded test plan shows error."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = None

        trigger_view_callback(mock_view, "on_run")

        mock_view.show_error.assert_called()
        mock_model_for_presenter.run_test.assert_not_called()

    def test_run_with_plan_calls_model(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Run with loaded plan calls model.run_test()."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_model_for_presenter._instrument_type = "power_supply"

        trigger_view_callback(mock_view, "on_run")

        mock_model_for_presenter.run_test.assert_called_once()

    def test_run_starts_timer(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Run starts runtime timer."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_model_for_presenter._instrument_type = "power_supply"

        trigger_view_callback(mock_view, "on_run")

        assert presenter._run_start_time is not None

    def test_run_clears_power_supply_position_for_sg_plan(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Run clears position indicator on pwoer supply plot for PS plan."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_model_for_presenter._instrument_type = "power_supply"

        trigger_view_callback(mock_view, "on_run")

        mock_view.power_supply_plot_panel.clear_position.assert_called()

    def test_run_clears_signal_gen_position_for_sg_plan(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_signal_generator_plan,
    ) -> None:
        """Run clears position on signal generator plot for SG plan."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_signal_generator_plan
        mock_model_for_presenter._instrument_type = "signal_generator"

        trigger_view_callback(mock_view, "on_run")

        mock_view.signal_gen_plot_panel.clear_position.assert_called()


class TestPauseHandler:
    """Tests for pause button handling."""

    def test_pause_calls_model_pause(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Pause button calls model.pause_test()."""
        trigger_view_callback(mock_view, "on_pause")

        mock_model_for_presenter.pause_test.assert_called_once()

    def test_pause_sets_status(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Pause button updates status."""
        trigger_view_callback(mock_view, "on_pause")

        calls = mock_view.set_status.call_args_list
        assert any("Paus" in str(call) for call in calls)


class TestStopHandler:
    """Tests for stop button handling."""

    def test_stop_calls_model_stop(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Stop button calls model.stop_test()."""
        trigger_view_callback(mock_view, "on_stop")

        mock_model_for_presenter.stop_test.assert_called_once()

    def test_stop_clears_pause_state(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Stop clears elapsed_at_pause if set."""
        presenter._elapsed_at_pause = 60.0

        trigger_view_callback(mock_view, "on_stop")

        assert presenter._elapsed_at_pause is None


class TestResumeHandler:
    """Tests for resume functionality (via run button when paused)."""

    def test_resume_from_paused_calls_model_resume(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Run button when paused calls model.resume_test()."""
        set_model_state(mock_model_for_presenter, EquipmentState.PAUSED)
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        trigger_view_callback(mock_view, "on_run")

        mock_model_for_presenter.resume_test.assert_called_once()
        mock_model_for_presenter.run_test.assert_not_called()

    def test_resume_restores_timer_from_elapsed(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Resume restores timer accounting for elapsed time."""
        set_model_state(mock_model_for_presenter, EquipmentState.PAUSED)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        presenter._elapsed_at_pause = 45.0

        trigger_view_callback(mock_view, "on_run")

        # Start time should be set to account for 45 seconds already elapsed
        assert presenter._run_start_time is not None
        # elapsed_at_pause should be cleared
        assert presenter._elapsed_at_pause is None

    def test_resume_sets_status(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Resume updates status message."""
        set_model_state(mock_model_for_presenter, EquipmentState.PAUSED)
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        trigger_view_callback(mock_view, "on_run")

        calls = mock_view.set_status.call_args_list
        assert any("Resum" in str(call) for call in calls)


class TestRuntimeTimer:
    """Tests for runtime timer management."""

    def test_timer_starts_on_run(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Timer starts when run is initiated."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_model_for_presenter._instrument_type = "power_supply"

        trigger_view_callback(mock_view, "on_run")

        assert presenter._run_start_time is not None
        mock_view.set_runtime_display.assert_called()

    def test_timer_updates_both_displays(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Timer updates both runtime and remaining time displays."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_model_for_presenter._instrument_type = "power_supply"

        trigger_view_callback(mock_view, "on_run")

        mock_view.set_runtime_display.assert_called()
        mock_view.set_remaining_time_display.assert_called()

    def test_timer_stops_on_complete(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Timer stops when test completes."""
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        presenter._run_start_time = time.time()
        presenter._runtime_timer_id = "timer_1"

        # Simulate transition to IDLE (test complete)
        trigger_state_change(
            mock_model_for_presenter, EquipmentState.RUNNING, EquipmentState.IDLE
        )
        execute_scheduled_callbacks(mock_view)

        assert presenter._run_start_time is None

    def test_timer_pauses_preserves_display(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Pausing timer preserves display values."""
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        presenter._run_start_time = time.time() - 30.0
        presenter._runtime_timer_id = "timer_1"

        # Record call counts before pause
        runtime_calls_before = mock_view.set_runtime_display.call_count

        trigger_state_change(
            mock_model_for_presenter, EquipmentState.RUNNING, EquipmentState.PAUSED
        )
        execute_scheduled_callbacks(mock_view)

        # Timer stopped but display not reset
        assert presenter._runtime_timer_id is None
        # run_start_time preserved (not cleared like normal stop)
        assert presenter._run_start_time is not None

    def test_multiple_pause_resume_cycles(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Multiple pause/resume cycles accumulate time correctly."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        # Start run
        trigger_view_callback(mock_view, "on_run")
        initial_start = presenter._run_start_time

        # Simulate 10 seconds passing, then pause
        presenter._run_start_time = time.time() - 10.0
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)
        trigger_state_change(
            mock_model_for_presenter, EquipmentState.RUNNING, EquipmentState.PAUSED
        )
        execute_scheduled_callbacks(mock_view)

        first_pause_elapsed = presenter._elapsed_at_pause
        assert first_pause_elapsed is not None
        assert 9.0 <= first_pause_elapsed <= 11.0

        # Resume
        set_model_state(mock_model_for_presenter, EquipmentState.PAUSED)
        trigger_view_callback(mock_view, "on_run")

        # elapsed_at_pause should be cleared
        assert presenter._elapsed_at_pause is None
        # run_start_time should be adjusted
        assert presenter._run_start_time is not None


class TestProgressCallback:
    """Tests for test progress updates."""

    def test_progress_updates_status_for_power_supply(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Progress callback updates status with power supply values."""
        step = PowerSupplyTestStep(
            step_number=3, duration_seconds=5.0, voltage=12.5, current=2.0
        )

        trigger_progress(mock_model_for_presenter, current=3, total=5, step=step)
        execute_scheduled_callbacks(mock_view)

        status_call = mock_view.set_status.call_args[0][0]
        assert "3/5" in status_call
        assert "12.5" in status_call or "12.50" in status_call

    def test_progress_updates_status_for_signal_generator(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Progress callback updates status with signal generator values."""
        step = SignalGeneratorTestStep(
            step_number=2, duration_seconds=5.0, frequency=1e6, power=-10.0
        )

        trigger_progress(mock_model_for_presenter, current=2, total=4, step=step)
        execute_scheduled_callbacks(mock_view)

        status_call = mock_view.set_status.call_args[0][0]
        assert "2/4" in status_call
        assert "MHz" in status_call
        assert "dBm" in status_call

    def test_progress_updates_power_supply_plot_position(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Progress updates position indicator on power supply plot."""
        step = PowerSupplyTestStep(
            step_number=1,
            duration_seconds=5.0,
            voltage=10.0,
            current=1.0,
            absolute_time_seconds=5.0,
        )

        trigger_progress(mock_model_for_presenter, current=1, total=3, step=step)
        execute_scheduled_callbacks(mock_view)

        mock_view.power_supply_plot_panel.set_current_position.assert_called_with(5.0)

    def test_progress_updates_signal_generator_plot_position(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Progress updates position indicator on signal generator plot."""
        step = SignalGeneratorTestStep(
            step_number=1,
            duration_seconds=7.5,
            frequency=2e6,
            power=-5.0,
            absolute_time_seconds=7.5,
        )

        trigger_progress(mock_model_for_presenter, current=1, total=2, step=step)
        execute_scheduled_callbacks(mock_view)

        mock_view.signal_gen_plot_panel.set_current_position.assert_called_with(7.5)

    def test_progress_highlights_power_supply_table_row(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Progress highlights current row in power supply table."""
        step = PowerSupplyTestStep(
            step_number=4, duration_seconds=5.0, voltage=20.0, current=3.0
        )

        trigger_progress(mock_model_for_presenter, current=4, total=5, step=step)
        execute_scheduled_callbacks(mock_view)

        mock_view.ps_table.highlight_step.assert_called_with(4)

    def test_progress_highlights_signal_generator_table_row(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Progress highlights current row in signal generator table."""
        step = SignalGeneratorTestStep(
            step_number=2, duration_seconds=5.0, frequency=3e6, power=-15.0
        )

        trigger_progress(mock_model_for_presenter, current=2, total=3, step=step)
        execute_scheduled_callbacks(mock_view)

        mock_view.sg_table.highlight_step.assert_called_with(2)


class TestCompleteCallback:
    """Tests for test completion handling."""

    def test_complete_success_shows_info(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Successful completion shows info dialog."""
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        trigger_complete(
            mock_model_for_presenter,
            success=True,
            message="Test completed successfully",
        )
        execute_scheduled_callbacks(mock_view)

        mock_view.show_info.assert_called_once()

    def test_complete_failure_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Failed completion shows error dialog."""
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        trigger_complete(
            mock_model_for_presenter, success=False, message="Connection lost"
        )
        execute_scheduled_callbacks(mock_view)

        mock_view.show_error.assert_called_once()

    def test_complete_clears_power_supply_plot_position(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Completion clears position indicator on power supply plot."""
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        trigger_complete(mock_model_for_presenter, success=True, message="Done")
        execute_scheduled_callbacks(mock_view)

        mock_view.power_supply_plot_panel.clear_position.assert_called()

    def test_complete_clears_signal_generator_plot_position(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_signal_generator_plan,
    ) -> None:
        """Completion clears position indicator on signal generator plot."""
        mock_model_for_presenter._test_plan = sample_signal_generator_plan

        trigger_complete(mock_model_for_presenter, success=True, message="Done")
        execute_scheduled_callbacks(mock_view)

        mock_view.signal_gen_plot_panel.clear_position.assert_called()

    def test_complete_clears_power_supply_table_highlight(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan,
    ) -> None:
        """Completion clears table row highlighting for power supply."""
        mock_model_for_presenter._test_plan = sample_power_supply_plan

        trigger_complete(mock_model_for_presenter, success=True, message="Done")
        execute_scheduled_callbacks(mock_view)

        mock_view.ps_table.clear_highlight.assert_called()

    def test_complete_clears_signal_generator_table_highlight(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_signal_generator_plan,
    ) -> None:
        """Completion clears table row highlighting for signal generator."""
        mock_model_for_presenter._test_plan = sample_signal_generator_plan

        trigger_complete(mock_model_for_presenter, success=True, message="Done")
        execute_scheduled_callbacks(mock_view)

        mock_view.sg_table.clear_highlight.assert_called()


class TestInstrumentDisplay:
    """Tests for single-instrument identification display."""

    def test_instrument_display_shows_connected_info(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Connected instrument info is shown."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter.get_instrument_identification.return_value = (
            "PS Model",
            "PS Tooltip",
        )

        # Trigger instrument display update
        presenter._update_instrument_display()

        mock_model_for_presenter.get_instrument_identification.assert_called()
        mock_view.set_instrument_display.assert_called_with("PS Model", "PS Tooltip")

    @pytest.mark.skip(reason="Tab change removed - single instrument shows only one tab")
    def test_signal_generator_tab_shows_signal_generator_info(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Signal generator tab shows signal generator instrument info."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_view.get_selected_tab_index.return_value = 1
        mock_model_for_presenter.get_instrument_identification.return_value = (
            "SG Model",
            "SG Tooltip",
        )

        presenter._on_tab_changed(None)

        mock_model_for_presenter.get_instrument_identification.assert_called_with(
            "signal_generator"
        )
        mock_view.set_instrument_display.assert_called_with("SG Model", "SG Tooltip")

    def test_instrument_display_cleared_when_not_connected(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Instrument display cleared when in UNKNOWN state."""
        set_model_state(mock_model_for_presenter, EquipmentState.UNKNOWN)

        presenter._update_instrument_display()

        mock_view.set_instrument_display.assert_called_with(None, None)

    def test_instrument_display_shown_when_running(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Instrument display shown when RUNNING."""
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)
        mock_model_for_presenter.get_instrument_identification.return_value = (
            "Model",
            "Tip",
        )

        presenter._update_instrument_display()

        mock_model_for_presenter.get_instrument_identification.assert_called()


class TestShutdown:
    """Tests for clean shutdown sequence."""

    def test_shutdown_stops_timer(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Shutdown stops runtime timer."""
        presenter._runtime_timer_id = "timer_1"
        presenter._run_start_time = time.time()

        presenter.shutdown()

        assert presenter._run_start_time is None
        mock_view.cancel_schedule.assert_called()

    def test_shutdown_disconnects_if_connected(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Shutdown disconnects if in connected state."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)

        presenter.shutdown()

        mock_model_for_presenter.disconnect.assert_called()

    def test_shutdown_disconnects_if_running(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Shutdown disconnects if in RUNNING state."""
        set_model_state(mock_model_for_presenter, EquipmentState.RUNNING)

        presenter.shutdown()

        mock_model_for_presenter.disconnect.assert_called()

    def test_shutdown_skips_disconnect_if_not_connected(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Shutdown skips disconnect if in UNKNOWN state."""
        set_model_state(mock_model_for_presenter, EquipmentState.UNKNOWN)

        presenter.shutdown()

        mock_model_for_presenter.disconnect.assert_not_called()

    def test_shutdown_handles_disconnect_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Shutdown handles disconnect errors gracefully."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_model_for_presenter.disconnect.side_effect = Exception("Network error")

        # Should not raise
        presenter.shutdown()


class TestStartFromHandler:
    """Tests for Start from / Resume from button handling."""

    def test_wires_callback(
        self, presenter: EquipmentPresenter, mock_view: Mock
    ) -> None:
        """Presenter registers start_from callback on view."""
        assert mock_view._callbacks["on_start_from"] is not None

    def test_no_selection_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Start from with no selected step shows error."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_view.get_active_table_selected_step.return_value = None
        trigger_view_callback(mock_view, "on_start_from")
        mock_view.show_error.assert_called()

    def test_no_plan_shows_error(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
    ) -> None:
        """Start from with no test plan shows error."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_view.get_active_table_selected_step.return_value = 3
        mock_model_for_presenter._test_plan = None
        trigger_view_callback(mock_view, "on_start_from")
        mock_view.show_error.assert_called()

    def test_shows_confirmation(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan: TestPlan,
    ) -> None:
        """Start from shows confirmation dialog with step details."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_view.get_active_table_selected_step.return_value = 2
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_view.show_confirmation.return_value = False
        trigger_view_callback(mock_view, "on_start_from")
        mock_view.show_confirmation.assert_called_once()

    def test_cancelled_does_nothing(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan: TestPlan,
    ) -> None:
        """Cancelling confirmation does not start test."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_view.get_active_table_selected_step.return_value = 2
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_view.show_confirmation.return_value = False
        trigger_view_callback(mock_view, "on_start_from")
        mock_model_for_presenter.run_test_from_step.assert_not_called()

    def test_confirmed_runs_from_step(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan: TestPlan,
    ) -> None:
        """Confirming starts test from selected step."""
        set_model_state(mock_model_for_presenter, EquipmentState.IDLE)
        mock_view.get_active_table_selected_step.return_value = 2
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_view.show_confirmation.return_value = True
        trigger_view_callback(mock_view, "on_start_from")
        mock_model_for_presenter.run_test_from_step.assert_called_once_with(2)

    def test_paused_stops_first(
        self,
        presenter: EquipmentPresenter,
        mock_model_for_presenter: Mock,
        mock_view: Mock,
        sample_power_supply_plan: TestPlan,
    ) -> None:
        """Resume from while paused calls stop_test first."""
        set_model_state(mock_model_for_presenter, EquipmentState.PAUSED)
        mock_view.get_active_table_selected_step.return_value = 2
        mock_model_for_presenter._test_plan = sample_power_supply_plan
        mock_view.show_confirmation.return_value = True
        trigger_view_callback(mock_view, "on_start_from")
        mock_model_for_presenter.stop_test.assert_called_once()
        assert presenter._pending_start_from is not None
