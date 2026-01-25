"""Tests for the test plan reader module."""

from pathlib import Path

import pytest

from visa_vulture.file_io.test_plan_reader import read_test_plan
from visa_vulture.model.test_plan import (
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
)


class TestReadTestPlanFileHandling:
    """Tests for file handling in read_test_plan."""

    def test_file_not_found_returns_error(self, tmp_path: Path) -> None:
        """Non-existent file returns error."""
        plan, errors = read_test_plan(tmp_path / "nonexistent.csv")

        assert plan is None
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_empty_file_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Empty file returns error."""
        plan, errors = read_test_plan(test_plan_fixtures_path / "invalid_empty.csv")

        assert plan is None
        assert len(errors) >= 1
        assert any("empty" in e.lower() or "no header" in e.lower() for e in errors)

    def test_no_data_rows_returns_error(self, tmp_path: Path) -> None:
        """File with only header returns error."""
        csv_path = tmp_path / "header_only.csv"
        csv_path.write_text("time,voltage,current\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("no data rows" in e.lower() for e in errors)


class TestReadPowerSupplyPlan:
    """Tests for power supply plan parsing."""

    def test_valid_power_supply_plan(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Valid power supply CSV is parsed correctly."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_POWER_SUPPLY
        assert plan.step_count == 3
        assert isinstance(plan.steps[0], PowerSupplyTestStep)

    def test_power_supply_step_values(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Power supply step values are parsed correctly."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert errors == []
        assert plan is not None

        step1 = plan.get_step(1)
        assert step1 is not None
        assert isinstance(step1, PowerSupplyTestStep)
        assert step1.time_seconds == 0.0
        assert step1.voltage == 5.0
        assert step1.current == 1.0
        assert step1.description == "Start"

    def test_power_supply_missing_columns_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Missing required columns returns error."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_missing_columns.csv"
        )

        assert plan is None
        # When columns are missing, the reader can't determine plan type
        assert any("cannot determine plan type" in e.lower() for e in errors)


class TestReadSignalGeneratorPlan:
    """Tests for signal generator plan parsing."""

    def test_valid_signal_generator_plan(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Valid signal generator CSV is parsed correctly."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator.csv"
        )

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR
        assert plan.step_count == 3
        assert isinstance(plan.steps[0], SignalGeneratorTestStep)

    def test_signal_generator_step_values(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Signal generator step values are parsed correctly."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator.csv"
        )

        assert errors == []
        assert plan is not None

        step1 = plan.get_step(1)
        assert step1 is not None
        assert isinstance(step1, SignalGeneratorTestStep)
        assert step1.time_seconds == 0.0
        assert step1.frequency == 1000000
        assert step1.power == 0
        assert step1.description == "Start at 1MHz"

    def test_signal_generator_negative_power_is_valid(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Negative power (dBm) values are valid."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator.csv"
        )

        assert errors == []
        assert plan is not None

        step2 = plan.get_step(2)
        assert step2 is not None
        assert isinstance(step2, SignalGeneratorTestStep)
        assert step2.power == -10


class TestReadTestPlanValueValidation:
    """Tests for value validation during parsing."""

    def test_invalid_time_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid time value returns error."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert plan is None
        assert any("invalid time value" in e.lower() for e in errors)

    def test_invalid_voltage_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid voltage value returns error."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert plan is None
        assert any("invalid voltage value" in e.lower() for e in errors)

    def test_invalid_current_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid current value returns error."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert plan is None
        assert any("invalid current value" in e.lower() for e in errors)

    def test_negative_time_returns_error(self, tmp_path: Path) -> None:
        """Negative time value returns error."""
        csv_path = tmp_path / "negative_time.csv"
        csv_path.write_text("time,voltage,current\n-1.0,5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("must be >= 0" in e for e in errors)

    def test_negative_voltage_returns_error(self, tmp_path: Path) -> None:
        """Negative voltage value returns error."""
        csv_path = tmp_path / "negative_voltage.csv"
        csv_path.write_text("time,voltage,current\n0.0,-5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("voltage" in e.lower() and ">= 0" in e for e in errors)

    def test_negative_current_returns_error(self, tmp_path: Path) -> None:
        """Negative current value returns error."""
        csv_path = tmp_path / "negative_current.csv"
        csv_path.write_text("time,voltage,current\n0.0,5.0,-1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("current" in e.lower() and ">= 0" in e for e in errors)

    def test_negative_frequency_returns_error(self, tmp_path: Path) -> None:
        """Negative frequency value returns error."""
        csv_path = tmp_path / "negative_freq.csv"
        csv_path.write_text("type,time,frequency,power\nsignal_generator,0.0,-1000,0\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("frequency" in e.lower() and ">= 0" in e for e in errors)


class TestReadTestPlanTypeDetection:
    """Tests for plan type detection."""

    def test_type_detected_from_explicit_column(self, tmp_path: Path) -> None:
        """Type is detected from 'type' column."""
        csv_path = tmp_path / "explicit_type.csv"
        csv_path.write_text(
            "type,time,frequency,power\nsignal_generator,0.0,1000000,0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR

    def test_type_inferred_from_power_supply_columns(
        self, tmp_path: Path
    ) -> None:
        """Type is inferred from power supply columns."""
        csv_path = tmp_path / "inferred_ps.csv"
        csv_path.write_text("time,voltage,current\n0.0,5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_POWER_SUPPLY

    def test_type_inferred_from_signal_generator_columns(
        self, tmp_path: Path
    ) -> None:
        """Type is inferred from signal generator columns."""
        csv_path = tmp_path / "inferred_sg.csv"
        csv_path.write_text("time,frequency,power\n0.0,1000000,0\n")

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR

    def test_ambiguous_type_returns_error(self, tmp_path: Path) -> None:
        """Ambiguous columns (both types) returns error."""
        csv_path = tmp_path / "ambiguous.csv"
        # Has columns for both power supply and signal generator
        csv_path.write_text("time,voltage,current,frequency,power\n0.0,5.0,1.0,1000,0\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("cannot determine plan type" in e.lower() for e in errors)

    def test_unknown_type_value_falls_back_to_columns(
        self, tmp_path: Path
    ) -> None:
        """Unknown type value falls back to column detection if columns match."""
        csv_path = tmp_path / "unknown_type.csv"
        # Has voltage/current columns, so falls back to power supply detection
        csv_path.write_text("type,time,voltage,current\nunknown_type,0.0,5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        # With matching columns, it successfully infers power_supply type
        assert errors == []
        assert plan is not None
        assert plan.plan_type == "power_supply"


class TestReadTestPlanColumnNormalization:
    """Tests for column name normalization."""

    def test_column_names_case_insensitive(self, tmp_path: Path) -> None:
        """Column names are case insensitive."""
        csv_path = tmp_path / "uppercase.csv"
        csv_path.write_text("TIME,VOLTAGE,CURRENT\n0.0,5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None

    def test_column_names_trimmed(self, tmp_path: Path) -> None:
        """Column names with whitespace are trimmed."""
        csv_path = tmp_path / "whitespace.csv"
        csv_path.write_text(" time , voltage , current \n0.0,5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None


class TestReadTestPlanStepNumbering:
    """Tests for step numbering."""

    def test_step_numbers_are_1_based(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Step numbers start at 1."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert errors == []
        assert plan is not None
        assert plan.get_step(1) is not None
        assert plan.get_step(0) is None

    def test_step_numbers_follow_row_order(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Step numbers follow CSV row order."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert errors == []
        assert plan is not None
        assert plan.steps[0].step_number == 1
        assert plan.steps[1].step_number == 2
        assert plan.steps[2].step_number == 3


class TestReadTestPlanName:
    """Tests for plan name derivation."""

    def test_plan_name_from_filename(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Plan name is derived from filename."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert errors == []
        assert plan is not None
        assert plan.name == "valid_power_supply"


class TestReadTestPlanValidation:
    """Tests for plan validation during reading."""

    def test_decreasing_times_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Decreasing times are caught by validation."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_decreasing_times.csv"
        )

        assert plan is None
        assert any("non-decreasing" in e.lower() for e in errors)


class TestReadTestPlanErrorAccumulation:
    """Tests for error accumulation."""

    def test_multiple_row_errors_accumulated(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Multiple row errors are all reported."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert plan is None
        # Should have errors for multiple rows with bad values
        assert len(errors) >= 2


class TestReadTestPlanPathTypes:
    """Tests for different path types."""

    def test_string_path_works(self, test_plan_fixtures_path: Path) -> None:
        """String path is accepted."""
        plan, errors = read_test_plan(
            str(test_plan_fixtures_path / "valid_power_supply.csv")
        )

        assert errors == []
        assert plan is not None

    def test_path_object_works(self, test_plan_fixtures_path: Path) -> None:
        """Path object is accepted."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert errors == []
        assert plan is not None
