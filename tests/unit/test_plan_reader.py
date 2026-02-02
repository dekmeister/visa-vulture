"""Tests for the test plan reader module."""

from pathlib import Path

import pytest

from visa_vulture.file_io.test_plan_reader import read_test_plan
from visa_vulture.model.test_plan import (
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    ModulationType,
    AMModulationConfig,
    FMModulationConfig,
)


class TestReadTestPlanFileHandling:
    """Tests for file handling in read_test_plan."""

    def test_file_not_found_returns_error(self, tmp_path: Path) -> None:
        """Non-existent file returns error."""
        result = read_test_plan(tmp_path / "nonexistent.csv")

        assert result.plan is None
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()

    def test_empty_file_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Empty file returns error."""
        result = read_test_plan(test_plan_fixtures_path / "invalid_empty.csv")

        assert result.plan is None
        assert len(result.errors) >= 1
        assert any("missing required metadata" in e.lower() for e in result.errors)

    def test_no_data_rows_returns_error(self, tmp_path: Path) -> None:
        """File with only header returns error."""
        csv_path = tmp_path / "header_only.csv"
        csv_path.write_text("# instrument_type: power_supply\nduration,voltage,current\n")

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("no data rows" in e.lower() for e in result.errors)


class TestReadPowerSupplyPlan:
    """Tests for power supply plan parsing."""

    def test_valid_power_supply_plan(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Valid power supply CSV is parsed correctly."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.plan_type == PLAN_TYPE_POWER_SUPPLY
        assert result.plan.step_count == 3
        assert isinstance(result.plan.steps[0], PowerSupplyTestStep)

    def test_power_supply_step_values(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Power supply step values are parsed correctly."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert result.errors == []
        assert result.plan is not None

        step1 = result.plan.get_step(1)
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
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_missing_columns.csv"
        )

        assert result.plan is None
        assert any("missing required columns" in e.lower() for e in result.errors)


class TestReadSignalGeneratorPlan:
    """Tests for signal generator plan parsing."""

    def test_valid_signal_generator_plan(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Valid signal generator CSV is parsed correctly."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR
        assert result.plan.step_count == 3
        assert isinstance(result.plan.steps[0], SignalGeneratorTestStep)

    def test_signal_generator_step_values(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Signal generator step values are parsed correctly."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator.csv"
        )

        assert result.errors == []
        assert result.plan is not None

        step1 = result.plan.get_step(1)
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
        result = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator.csv"
        )

        assert result.errors == []
        assert result.plan is not None

        step2 = result.plan.get_step(2)
        assert step2 is not None
        assert isinstance(step2, SignalGeneratorTestStep)
        assert step2.power == -10


class TestReadTestPlanValueValidation:
    """Tests for value validation during parsing."""

    def test_invalid_duration_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid duration value returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert result.plan is None
        assert any("invalid duration value" in e.lower() for e in result.errors)

    def test_invalid_voltage_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid voltage value returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert result.plan is None
        assert any("invalid voltage value" in e.lower() for e in result.errors)

    def test_invalid_current_value_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid current value returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert result.plan is None
        assert any("invalid current value" in e.lower() for e in result.errors)

    def test_negative_duration_returns_error(self, tmp_path: Path) -> None:
        """Negative duration value returns error."""
        csv_path = tmp_path / "negative_duration.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nduration,voltage,current\n-1.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("must be >= 0" in e for e in result.errors)

    def test_negative_voltage_returns_error(self, tmp_path: Path) -> None:
        """Negative voltage value returns error."""
        csv_path = tmp_path / "negative_voltage.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nduration,voltage,current\n0.0,-5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("voltage" in e.lower() and ">= 0" in e for e in result.errors)

    def test_negative_current_returns_error(self, tmp_path: Path) -> None:
        """Negative current value returns error."""
        csv_path = tmp_path / "negative_current.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nduration,voltage,current\n0.0,5.0,-1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("current" in e.lower() and ">= 0" in e for e in result.errors)

    def test_negative_frequency_returns_error(self, tmp_path: Path) -> None:
        """Negative frequency value returns error."""
        csv_path = tmp_path / "negative_freq.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n0.0,-1000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("frequency" in e.lower() and ">= 0" in e for e in result.errors)


class TestReadTestPlanTypeDetection:
    """Tests for plan type detection via metadata."""

    def test_type_detected_from_metadata(self, tmp_path: Path) -> None:
        """Type is detected from instrument_type metadata."""
        csv_path = tmp_path / "metadata_type.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n0.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR

    def test_missing_metadata_returns_error(self, tmp_path: Path) -> None:
        """CSV with no metadata comment lines returns error."""
        csv_path = tmp_path / "no_metadata.csv"
        csv_path.write_text("duration,voltage,current\n0.0,5.0,1.0\n")

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("missing required metadata" in e.lower() for e in result.errors)

    def test_missing_instrument_type_metadata_returns_error(
        self, tmp_path: Path
    ) -> None:
        """Metadata present but missing instrument_type returns error."""
        csv_path = tmp_path / "wrong_metadata.csv"
        csv_path.write_text(
            "# description: some test plan\n"
            "duration,voltage,current\n0.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("missing required metadata field" in e.lower() for e in result.errors)

    def test_invalid_instrument_type_returns_error(
        self, tmp_path: Path
    ) -> None:
        """Invalid instrument_type value returns error with no fallback."""
        csv_path = tmp_path / "bad_type.csv"
        csv_path.write_text(
            "# instrument_type: unknown_type\n"
            "duration,voltage,current\n0.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("invalid instrument_type" in e.lower() for e in result.errors)

    def test_metadata_whitespace_handling(self, tmp_path: Path) -> None:
        """Metadata with extra whitespace is parsed correctly."""
        csv_path = tmp_path / "whitespace_metadata.csv"
        csv_path.write_text(
            "#  instrument_type :  power_supply \n"
            "duration,voltage,current\n0.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.plan_type == PLAN_TYPE_POWER_SUPPLY


class TestReadTestPlanColumnNormalization:
    """Tests for column name normalization."""

    def test_column_names_case_insensitive(self, tmp_path: Path) -> None:
        """Column names are case insensitive."""
        csv_path = tmp_path / "uppercase.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\nDURATION,VOLTAGE,CURRENT\n0.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None

    def test_column_names_trimmed(self, tmp_path: Path) -> None:
        """Column names with whitespace are trimmed."""
        csv_path = tmp_path / "whitespace.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n duration , voltage , current \n0.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None


class TestReadTestPlanStepNumbering:
    """Tests for step numbering."""

    def test_step_numbers_are_1_based(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Step numbers start at 1."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.get_step(1) is not None
        assert result.plan.get_step(0) is None

    def test_step_numbers_follow_row_order(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Step numbers follow CSV row order."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.steps[0].step_number == 1
        assert result.plan.steps[1].step_number == 2
        assert result.plan.steps[2].step_number == 3


class TestReadTestPlanName:
    """Tests for plan name derivation."""

    def test_plan_name_from_filename(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Plan name is derived from filename."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.name == "valid_power_supply"


class TestReadTestPlanErrorAccumulation:
    """Tests for error accumulation."""

    def test_multiple_row_errors_accumulated(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Multiple row errors are all reported."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_bad_values.csv"
        )

        assert result.plan is None
        # Should have errors for multiple rows with bad values
        assert len(result.errors) >= 2


class TestReadTestPlanPathTypes:
    """Tests for different path types."""

    def test_string_path_works(self, test_plan_fixtures_path: Path) -> None:
        """String path is accepted."""
        result = read_test_plan(
            str(test_plan_fixtures_path / "valid_power_supply.csv")
        )

        assert result.errors == []
        assert result.plan is not None

    def test_path_object_works(self, test_plan_fixtures_path: Path) -> None:
        """Path object is accepted."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_power_supply.csv"
        )

        assert result.errors == []
        assert result.plan is not None


class TestReadSignalGeneratorPlanWithModulation:
    """Tests for signal generator plan parsing with modulation metadata."""

    def test_am_modulation_metadata_parsed(self, tmp_path: Path) -> None:
        """AM modulation metadata is parsed correctly."""
        csv_path = tmp_path / "am_test.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: 1000\n"
            "# am_depth: 50\n"
            "duration,frequency,power,modulation_enabled\n"
            "1.0,1000000,0,true\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.modulation_config is not None
        assert isinstance(result.plan.modulation_config, AMModulationConfig)
        assert result.plan.modulation_config.modulation_type == ModulationType.AM
        assert result.plan.modulation_config.modulation_frequency == 1000.0
        assert result.plan.modulation_config.depth == 50.0

    def test_fm_modulation_metadata_parsed(self, tmp_path: Path) -> None:
        """FM modulation metadata is parsed correctly."""
        csv_path = tmp_path / "fm_test.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: fm\n"
            "# modulation_frequency: 1000\n"
            "# fm_deviation: 5000\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert isinstance(result.plan.modulation_config, FMModulationConfig)
        assert result.plan.modulation_config.modulation_type == ModulationType.FM
        assert result.plan.modulation_config.modulation_frequency == 1000.0
        assert result.plan.modulation_config.deviation == 5000.0

    def test_no_modulation_type_results_in_none_config(self, tmp_path: Path) -> None:
        """Without modulation_type, modulation_config is None."""
        csv_path = tmp_path / "no_mod.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.modulation_config is None

    def test_missing_modulation_frequency_returns_error(self, tmp_path: Path) -> None:
        """Missing modulation_frequency with modulation_type returns error."""
        csv_path = tmp_path / "missing_freq.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# am_depth: 50\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("modulation_frequency" in e for e in result.errors)

    def test_missing_am_depth_returns_error(self, tmp_path: Path) -> None:
        """Missing am_depth for AM modulation returns error."""
        csv_path = tmp_path / "missing_depth.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: 1000\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("am_depth" in e for e in result.errors)

    def test_missing_fm_deviation_returns_error(self, tmp_path: Path) -> None:
        """Missing fm_deviation for FM modulation returns error."""
        csv_path = tmp_path / "missing_dev.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: fm\n"
            "# modulation_frequency: 1000\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("fm_deviation" in e for e in result.errors)

    def test_invalid_modulation_type_returns_error(self, tmp_path: Path) -> None:
        """Invalid modulation_type returns error."""
        csv_path = tmp_path / "bad_mod_type.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: invalid\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("invalid modulation_type" in e.lower() for e in result.errors)

    def test_modulation_enabled_column_parsed_true_values(
        self, tmp_path: Path
    ) -> None:
        """modulation_enabled column parses true values correctly."""
        csv_path = tmp_path / "mod_enabled.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: 1000\n"
            "# am_depth: 50\n"
            "duration,frequency,power,modulation_enabled\n"
            "1.0,1000000,0,true\n"
            "1.0,2000000,-10,1\n"
            "1.0,3000000,-5,yes\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.steps[0].modulation_enabled is True
        assert result.plan.steps[1].modulation_enabled is True
        assert result.plan.steps[2].modulation_enabled is True

    def test_modulation_enabled_column_parsed_false_values(
        self, tmp_path: Path
    ) -> None:
        """modulation_enabled column parses false values correctly."""
        csv_path = tmp_path / "mod_disabled.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power,modulation_enabled\n"
            "1.0,1000000,0,false\n"
            "1.0,2000000,-10,0\n"
            "1.0,3000000,-5,no\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.steps[0].modulation_enabled is False
        assert result.plan.steps[1].modulation_enabled is False
        assert result.plan.steps[2].modulation_enabled is False

    def test_modulation_enabled_defaults_to_false(self, tmp_path: Path) -> None:
        """Missing modulation_enabled column defaults to False."""
        csv_path = tmp_path / "no_mod_col.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.steps[0].modulation_enabled is False

    def test_invalid_modulation_enabled_value_returns_error(
        self, tmp_path: Path
    ) -> None:
        """Invalid modulation_enabled value returns error."""
        csv_path = tmp_path / "bad_mod_enabled.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power,modulation_enabled\n"
            "1.0,1000000,0,maybe\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("modulation_enabled" in e for e in result.errors)

    def test_invalid_am_depth_value_returns_error(self, tmp_path: Path) -> None:
        """Invalid am_depth value returns error."""
        csv_path = tmp_path / "bad_depth.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: 1000\n"
            "# am_depth: notanumber\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("am_depth" in e for e in result.errors)

    def test_am_depth_out_of_range_returns_error(self, tmp_path: Path) -> None:
        """AM depth outside 0-100 range returns error."""
        csv_path = tmp_path / "depth_over.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: 1000\n"
            "# am_depth: 150\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("0-100" in e for e in result.errors)

    def test_invalid_modulation_frequency_returns_error(self, tmp_path: Path) -> None:
        """Invalid modulation_frequency value returns error."""
        csv_path = tmp_path / "bad_freq.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: notanumber\n"
            "# am_depth: 50\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("modulation_frequency" in e for e in result.errors)

    def test_zero_modulation_frequency_returns_error(self, tmp_path: Path) -> None:
        """Zero modulation_frequency returns error."""
        csv_path = tmp_path / "zero_freq.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "# modulation_type: am\n"
            "# modulation_frequency: 0\n"
            "# am_depth: 50\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("modulation_frequency must be > 0" in e for e in result.errors)


class TestReadSignalGeneratorPlanModulationValidationFixtures:
    """Tests for signal generator modulation validation using fixture files."""

    def test_missing_am_depth_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Missing am_depth in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_missing_am_depth.csv"
        )

        assert result.plan is None
        assert any("am_depth" in e for e in result.errors)

    def test_missing_fm_deviation_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Missing fm_deviation in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_missing_fm_deviation.csv"
        )

        assert result.plan is None
        assert any("fm_deviation" in e for e in result.errors)

    def test_missing_modulation_frequency_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Missing modulation_frequency in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_missing_mod_freq.csv"
        )

        assert result.plan is None
        assert any("modulation_frequency" in e for e in result.errors)

    def test_bad_modulation_type_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid modulation_type in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_bad_modulation_type.csv"
        )

        assert result.plan is None
        assert any("invalid modulation_type" in e.lower() for e in result.errors)

    def test_am_depth_over_100_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """AM depth over 100% in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_am_depth_over_100.csv"
        )

        assert result.plan is None
        assert any("0-100" in e for e in result.errors)

    def test_negative_am_depth_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Negative AM depth in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_negative_am_depth.csv"
        )

        assert result.plan is None
        assert any("0-100" in e for e in result.errors)

    def test_zero_modulation_frequency_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Zero modulation_frequency in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_zero_mod_freq.csv"
        )

        assert result.plan is None
        assert any("modulation_frequency must be > 0" in e for e in result.errors)

    def test_negative_fm_deviation_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Negative FM deviation in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_negative_fm_deviation.csv"
        )

        assert result.plan is None
        assert any("fm_deviation must be > 0" in e for e in result.errors)

    def test_bad_modulation_enabled_value_fixture_returns_error(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Invalid modulation_enabled value in fixture file returns error."""
        result = read_test_plan(
            test_plan_fixtures_path / "invalid_sg_bad_mod_enabled_value.csv"
        )

        assert result.plan is None
        assert any("modulation_enabled" in e for e in result.errors)

    def test_valid_am_fixture_loads_correctly(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Valid AM modulation fixture loads correctly."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator_am.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.modulation_config is not None
        assert result.plan.modulation_config.modulation_type == ModulationType.AM
        assert result.plan.step_count == 3
        # Check modulation_enabled values match the fixture
        assert result.plan.steps[0].modulation_enabled is True
        assert result.plan.steps[1].modulation_enabled is False
        assert result.plan.steps[2].modulation_enabled is True

    def test_valid_fm_fixture_loads_correctly(
        self, test_plan_fixtures_path: Path
    ) -> None:
        """Valid FM modulation fixture loads correctly."""
        result = read_test_plan(
            test_plan_fixtures_path / "valid_signal_generator_fm.csv"
        )

        assert result.errors == []
        assert result.plan is not None
        assert result.plan.modulation_config is not None
        assert result.plan.modulation_config.modulation_type == ModulationType.FM
        assert result.plan.step_count == 3


class TestHardLimitValidation:
    """Tests for hard limit validation during parsing (errors that block loading)."""

    def test_power_below_hard_minimum_returns_error(self, tmp_path: Path) -> None:
        """Power below -200 dBm returns error."""
        csv_path = tmp_path / "power_too_low.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,-250\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("power" in e.lower() and "-200" in e for e in result.errors)

    def test_power_above_hard_maximum_returns_error(self, tmp_path: Path) -> None:
        """Power above +60 dBm returns error."""
        csv_path = tmp_path / "power_too_high.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,100\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("power" in e.lower() and "60" in e for e in result.errors)

    def test_frequency_above_hard_maximum_returns_error(self, tmp_path: Path) -> None:
        """Frequency above 100 THz returns error."""
        csv_path = tmp_path / "freq_too_high.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,200000000000000,0\n"  # 200 THz
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("frequency" in e.lower() and "exceeds" in e.lower() for e in result.errors)

    def test_voltage_above_hard_maximum_returns_error(self, tmp_path: Path) -> None:
        """Voltage above 10kV returns error."""
        csv_path = tmp_path / "voltage_too_high.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n"
            "duration,voltage,current\n"
            "1.0,15000,1.0\n"  # 15kV
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("voltage" in e.lower() and "exceeds" in e.lower() for e in result.errors)

    def test_current_above_hard_maximum_returns_error(self, tmp_path: Path) -> None:
        """Current above 1000A returns error."""
        csv_path = tmp_path / "current_too_high.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n"
            "duration,voltage,current\n"
            "1.0,5.0,1500\n"  # 1500A
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert any("current" in e.lower() and "exceeds" in e.lower() for e in result.errors)

    def test_power_at_hard_minimum_is_valid(self, tmp_path: Path) -> None:
        """Power exactly at -200 dBm is valid."""
        csv_path = tmp_path / "power_at_min.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,-200\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None

    def test_power_at_hard_maximum_is_valid(self, tmp_path: Path) -> None:
        """Power exactly at +60 dBm is valid."""
        csv_path = tmp_path / "power_at_max.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,60\n"
        )

        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None


class TestSoftLimitValidation:
    """Tests for soft limit validation (warnings that allow loading)."""

    def test_power_below_soft_minimum_returns_warning(self, tmp_path: Path) -> None:
        """Power below soft limit generates warning but plan loads."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "power_low.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,-150\n"  # Below default -100 dBm soft limit
        )

        limits = ValidationLimits()  # Use defaults
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 1
        assert any("power" in w.lower() and "noise floor" in w.lower() for w in result.warnings)

    def test_power_above_soft_maximum_returns_warning(self, tmp_path: Path) -> None:
        """Power above soft limit generates warning but plan loads."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "power_high.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,50\n"  # Above default +30 dBm soft limit
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 1
        assert any("power" in w.lower() and "exceeds" in w.lower() for w in result.warnings)

    def test_frequency_below_soft_minimum_returns_warning(self, tmp_path: Path) -> None:
        """Frequency below soft limit generates warning but plan loads."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "freq_low.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,0.5,0\n"  # Below default 1 Hz soft limit
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 1
        assert any("frequency" in w.lower() and "low" in w.lower() for w in result.warnings)

    def test_voltage_above_soft_maximum_returns_warning(self, tmp_path: Path) -> None:
        """Voltage above soft limit generates warning but plan loads."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "voltage_high.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n"
            "duration,voltage,current\n"
            "1.0,200,1.0\n"  # Above default 100V soft limit
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 1
        assert any("voltage" in w.lower() and "exceeds" in w.lower() for w in result.warnings)

    def test_duration_above_soft_maximum_returns_warning(self, tmp_path: Path) -> None:
        """Duration above soft limit generates warning but plan loads."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "duration_long.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n"
            "duration,voltage,current\n"
            "100000,5.0,1.0\n"  # Above default 86400s (24h) soft limit
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 1
        assert any("duration" in w.lower() for w in result.warnings)

    def test_custom_soft_limits_respected(self, tmp_path: Path) -> None:
        """Custom soft limits from config are used."""
        from visa_vulture.config.schema import (
            ValidationLimits,
            SignalGeneratorSoftLimits,
        )

        csv_path = tmp_path / "custom_limit.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,15\n"  # Would be OK with default +30, but custom is +10
        )

        # Custom limit: power max is +10 dBm
        custom_sg_limits = SignalGeneratorSoftLimits(power_max_dbm=10.0)
        limits = ValidationLimits(signal_generator=custom_sg_limits)
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 1
        assert any("power" in w.lower() for w in result.warnings)

    def test_no_warnings_for_valid_values(self, tmp_path: Path) -> None:
        """Values within soft limits generate no warnings."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "all_valid.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,0\n"  # All values within soft limits
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert result.warnings == []

    def test_multiple_warnings_accumulated(self, tmp_path: Path) -> None:
        """Multiple soft limit violations generate multiple warnings."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "multiple_warnings.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,-150\n"  # Power below soft limit
            "1.0,1000000,50\n"  # Power above soft limit
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.errors == []
        assert result.plan is not None
        assert len(result.warnings) >= 2

    def test_soft_limit_validation_skipped_without_limits(self, tmp_path: Path) -> None:
        """Without soft_limits parameter, no warnings are generated."""
        csv_path = tmp_path / "no_limits.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,-150\n"  # Would trigger warning if limits provided
        )

        # No soft_limits parameter
        result = read_test_plan(csv_path)

        assert result.errors == []
        assert result.plan is not None
        assert result.warnings == []


class TestTestPlanResult:
    """Tests for TestPlanResult dataclass."""

    def test_result_with_successful_parse(self, tmp_path: Path) -> None:
        """Result with successful parse has plan and empty error list."""
        csv_path = tmp_path / "valid.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n"
            "duration,voltage,current\n"
            "1.0,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is not None
        assert result.errors == []
        assert result.warnings == []

    def test_result_with_errors_has_no_plan(self, tmp_path: Path) -> None:
        """Result with errors has None plan."""
        csv_path = tmp_path / "invalid.csv"
        csv_path.write_text(
            "# instrument_type: power_supply\n"
            "duration,voltage,current\n"
            "invalid,5.0,1.0\n"
        )

        result = read_test_plan(csv_path)

        assert result.plan is None
        assert len(result.errors) >= 1

    def test_result_with_warnings_has_plan(self, tmp_path: Path) -> None:
        """Result with warnings still has valid plan."""
        from visa_vulture.config.schema import ValidationLimits

        csv_path = tmp_path / "with_warnings.csv"
        csv_path.write_text(
            "# instrument_type: signal_generator\n"
            "duration,frequency,power\n"
            "1.0,1000000,-150\n"  # Triggers soft limit warning
        )

        limits = ValidationLimits()
        result = read_test_plan(csv_path, soft_limits=limits)

        assert result.plan is not None
        assert result.errors == []
        assert len(result.warnings) >= 1
