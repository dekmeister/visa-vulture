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
        assert any("missing required metadata" in e.lower() for e in errors)

    def test_no_data_rows_returns_error(self, tmp_path: Path) -> None:
        """File with only header returns error."""
        csv_path = tmp_path / "header_only.csv"
        csv_path.write_text("# instrument_type: power_supply\nduration,voltage,current\n")

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
        assert step1.duration_seconds == 1.0
        assert step1.absolute_time_seconds == 0.0
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
        assert any("missing required columns" in e.lower() for e in errors)


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
        assert step1.duration_seconds == 1.0
        assert step1.absolute_time_seconds == 0.0
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

    def test_invalid_duration_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid duration value returns error."""
        plan, errors = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert plan is None
        assert any("invalid duration value" in e.lower() for e in errors)

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

    def test_negative_duration_returns_error(self, tmp_path: Path) -> None:
        """Negative duration value returns error."""
        csv_path = tmp_path / "negative_duration.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nduration,voltage,current\n-1.0,5.0,1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("must be >= 0" in e for e in errors)

    def test_negative_voltage_returns_error(self, tmp_path: Path) -> None:
        """Negative voltage value returns error."""
        csv_path = tmp_path / "negative_voltage.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nduration,voltage,current\n0.0,-5.0,1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("voltage" in e.lower() and ">= 0" in e for e in errors)

    def test_negative_current_returns_error(self, tmp_path: Path) -> None:
        """Negative current value returns error."""
        csv_path = tmp_path / "negative_current.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nduration,voltage,current\n0.0,5.0,-1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("current" in e.lower() and ">= 0" in e for e in errors)

    def test_negative_frequency_returns_error(self, tmp_path: Path) -> None:
        """Negative frequency value returns error."""
        csv_path = tmp_path / "negative_freq.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n0.0,-1000,0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("frequency" in e.lower() and ">= 0" in e for e in errors)


class TestReadTestPlanTypeDetection:
    """Tests for plan type detection via metadata."""

    def test_type_detected_from_metadata(self, tmp_path: Path) -> None:
        """Type is detected from instrument_type metadata."""
        csv_path = tmp_path / "metadata_type.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n0.0,1000000,0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR

    def test_missing_metadata_returns_error(self, tmp_path: Path) -> None:
        """CSV with no metadata comment lines returns error."""
        csv_path = tmp_path / "no_metadata.csv"
        csv_path.write_text("duration,voltage,current\n0.0,5.0,1.0\n")

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("missing required metadata" in e.lower() for e in errors)

    def test_missing_instrument_type_metadata_returns_error(
        self, tmp_path: Path
    ) -> None:
        """Metadata present but missing instrument_type returns error."""
        csv_path = tmp_path / "wrong_metadata.csv"
        csv_path.write_text(
            "# description: some test plan\n"
            "duration,voltage,current\n0.0,5.0,1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("missing required metadata field" in e.lower() for e in errors)

    def test_invalid_instrument_type_returns_error(
        self, tmp_path: Path
    ) -> None:
        """Invalid instrument_type value returns error with no fallback."""
        csv_path = tmp_path / "bad_type.csv"
        csv_path.write_text(
            "# instrument_type: unknown_type\n"
            "duration,voltage,current\n0.0,5.0,1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert plan is None
        assert any("invalid instrument_type" in e.lower() for e in errors)

    def test_metadata_whitespace_handling(self, tmp_path: Path) -> None:
        """Metadata with extra whitespace is parsed correctly."""
        csv_path = tmp_path / "whitespace_metadata.csv"
        csv_path.write_text(
            "#  instrument_type :  power_supply \n"
            "duration,voltage,current\n0.0,5.0,1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None
        assert plan.plan_type == PLAN_TYPE_POWER_SUPPLY


class TestReadTestPlanColumnNormalization:
    """Tests for column name normalization."""

    def test_column_names_case_insensitive(self, tmp_path: Path) -> None:
        """Column names are case insensitive."""
        csv_path = tmp_path / "uppercase.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nDURATION,VOLTAGE,CURRENT\n0.0,5.0,1.0\n"
        )

        plan, errors = read_test_plan(csv_path)

        assert errors == []
        assert plan is not None

    def test_column_names_trimmed(self, tmp_path: Path) -> None:
        """Column names with whitespace are trimmed."""
        csv_path = tmp_path / "whitespace.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n duration , voltage , current \n0.0,5.0,1.0\n"
        )

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
