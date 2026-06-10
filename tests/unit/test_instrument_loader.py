"""Tests for instrument loader and auto-scanning."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from visa_vulture.instruments import (
    BaseInstrument,
    PowerSupply,
    SignalGenerator,
)
from visa_vulture.instruments.instrument_loader import (
    InstrumentEntry,
    build_instrument_registry,
    create_instrument,
    scan_custom_instruments,
    _get_base_type,
)

# === Helper classes for testing ===


class FakeSignalGen(SignalGenerator):
    """Test custom signal generator."""

    display_name = "Fake Signal Gen"


class FakePowerSupply(PowerSupply):
    """Test custom power supply."""

    display_name = "Fake PS"


class NoDisplayName(SignalGenerator):
    """Custom class without display_name."""

    pass


class DirectBaseSubclass(BaseInstrument):
    """Directly extends BaseInstrument (should be rejected)."""

    display_name = "Bad Instrument"

    def get_status(self) -> dict:
        return {}


# Base-type map and built-in entries the composer (main.py) would supply,
# reproduced here so the loader tests exercise the same shape.
_BASE_MAP = {PowerSupply: "power_supply", SignalGenerator: "signal_generator"}
_BUILTINS = {
    "Power Supply": InstrumentEntry(
        cls=PowerSupply,
        display_name="Power Supply",
        instrument_type="power_supply",
        is_builtin=True,
    ),
    "Signal Generator": InstrumentEntry(
        cls=SignalGenerator,
        display_name="Signal Generator",
        instrument_type="signal_generator",
        is_builtin=True,
    ),
}


# === Tests for _get_base_type ===


class TestGetBaseType:
    def test_signal_generator_subclass(self):
        assert _get_base_type(FakeSignalGen, _BASE_MAP) == "signal_generator"

    def test_power_supply_subclass(self):
        assert _get_base_type(FakePowerSupply, _BASE_MAP) == "power_supply"

    def test_signal_generator_itself(self):
        assert _get_base_type(SignalGenerator, _BASE_MAP) == "signal_generator"

    def test_power_supply_itself(self):
        assert _get_base_type(PowerSupply, _BASE_MAP) == "power_supply"

    def test_base_instrument_returns_none(self):
        assert _get_base_type(BaseInstrument, _BASE_MAP) is None

    def test_unrelated_class_returns_none(self):
        assert _get_base_type(str, _BASE_MAP) is None


# === Tests for build_instrument_registry ===


class TestBuildInstrumentRegistry:
    def test_built_in_types_included(self):
        registry = build_instrument_registry(_BUILTINS)
        assert "Power Supply" in registry
        assert "Signal Generator" in registry
        assert registry["Power Supply"].cls is PowerSupply
        assert registry["Signal Generator"].cls is SignalGenerator

    def test_built_in_base_types(self):
        registry = build_instrument_registry(_BUILTINS)
        assert registry["Power Supply"].instrument_type == "power_supply"
        assert registry["Signal Generator"].instrument_type == "signal_generator"

    def test_custom_instruments_merged(self):
        custom = {
            "Fake Signal Gen": InstrumentEntry(
                cls=FakeSignalGen,
                display_name="Fake Signal Gen",
                instrument_type="signal_generator",
            )
        }
        registry = build_instrument_registry(_BUILTINS, custom)
        assert "Fake Signal Gen" in registry
        assert "Power Supply" in registry
        assert "Signal Generator" in registry

    def test_empty_custom_dict(self):
        registry = build_instrument_registry(_BUILTINS, {})
        assert len(registry) == 2

    def test_none_custom_dict(self):
        registry = build_instrument_registry(_BUILTINS, None)
        assert len(registry) == 2


# === Tests for create_instrument ===


class TestCreateInstrument:
    def test_create_built_in_power_supply(self):
        registry = build_instrument_registry(_BUILTINS)
        instrument = create_instrument(
            registry, "Power Supply", "TCPIP::1.2.3.4::INSTR", 5000
        )
        assert isinstance(instrument, PowerSupply)
        assert instrument.name == "Power Supply"

    def test_create_built_in_signal_generator(self):
        registry = build_instrument_registry(_BUILTINS)
        instrument = create_instrument(
            registry, "Signal Generator", "TCPIP::1.2.3.4::INSTR", 5000
        )
        assert isinstance(instrument, SignalGenerator)

    def test_create_custom_instrument(self):
        custom = {
            "Fake Signal Gen": InstrumentEntry(
                cls=FakeSignalGen,
                display_name="Fake Signal Gen",
                instrument_type="signal_generator",
            )
        }
        registry = build_instrument_registry(_BUILTINS, custom)
        instrument = create_instrument(
            registry, "Fake Signal Gen", "TCPIP::1.2.3.4::INSTR", 5000
        )
        assert isinstance(instrument, FakeSignalGen)
        assert isinstance(instrument, SignalGenerator)

    def test_custom_instrument_passes_isinstance_check(self):
        """Custom instrument must pass isinstance for parent type."""
        custom = {
            "Fake Signal Gen": InstrumentEntry(
                cls=FakeSignalGen,
                display_name="Fake Signal Gen",
                instrument_type="signal_generator",
            )
        }
        registry = build_instrument_registry(_BUILTINS, custom)
        instrument = create_instrument(
            registry, "Fake Signal Gen", "TCPIP::1.2.3.4::INSTR", 5000
        )
        assert isinstance(instrument, SignalGenerator)
        assert isinstance(instrument, BaseInstrument)

    def test_unknown_display_name_raises(self):
        registry = build_instrument_registry(_BUILTINS)
        with pytest.raises(ValueError, match="Unknown instrument"):
            create_instrument(registry, "Nonexistent", "TCPIP::1.2.3.4::INSTR", 5000)


# === Tests for scan_custom_instruments ===


class TestScanCustomInstruments:
    def test_nonexistent_directory_returns_empty(self, tmp_path):
        result = scan_custom_instruments(tmp_path / "does_not_exist", _BASE_MAP)
        assert result == {}

    def test_empty_directory_returns_empty(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert result == {}

    def test_discovers_valid_custom_instrument(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "my_sig_gen.py").write_text(
            "from visa_vulture.instruments import SignalGenerator\n"
            "\n"
            "class MySigGen(SignalGenerator):\n"
            '    display_name = "My Sig Gen"\n'
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert "My Sig Gen" in result
        assert result["My Sig Gen"].instrument_type == "signal_generator"
        assert result["My Sig Gen"].display_name == "My Sig Gen"

    def test_discovers_power_supply_extension(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "my_ps.py").write_text(
            "from visa_vulture.instruments import PowerSupply\n"
            "\n"
            "class MyPS(PowerSupply):\n"
            '    display_name = "My Power Supply"\n'
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert "My Power Supply" in result
        assert result["My Power Supply"].instrument_type == "power_supply"

    def test_skips_class_without_display_name(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "no_name.py").write_text(
            "from visa_vulture.instruments import SignalGenerator\n"
            "\n"
            "class NoName(SignalGenerator):\n"
            "    pass\n"
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert result == {}

    def test_rejects_direct_base_instrument_subclass(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "bad_instr.py").write_text(
            "from visa_vulture.instruments import BaseInstrument\n"
            "\n"
            "class BadInstrument(BaseInstrument):\n"
            '    display_name = "Bad"\n'
            "    def get_status(self):\n"
            "        return {}\n"
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert result == {}

    def test_skips_modules_with_import_errors(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "broken.py").write_text("import nonexistent_module\n")

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert result == {}

    def test_skips_dunder_files(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text(
            "from visa_vulture.instruments import SignalGenerator\n"
            "\n"
            "class InitSigGen(SignalGenerator):\n"
            '    display_name = "Init Sig Gen"\n'
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert result == {}

    def test_multiple_instruments_in_directory(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "sig_gen_a.py").write_text(
            "from visa_vulture.instruments import SignalGenerator\n"
            "\n"
            "class SigGenA(SignalGenerator):\n"
            '    display_name = "Sig Gen A"\n'
        )
        (instruments_dir / "ps_b.py").write_text(
            "from visa_vulture.instruments import PowerSupply\n"
            "\n"
            "class PSB(PowerSupply):\n"
            '    display_name = "PS B"\n'
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert len(result) == 2
        assert "Sig Gen A" in result
        assert "PS B" in result

    def test_discovered_custom_is_not_builtin(self, tmp_path):
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "my_sig_gen.py").write_text(
            "from visa_vulture.instruments import SignalGenerator\n"
            "\n"
            "class MySigGen(SignalGenerator):\n"
            '    display_name = "My Sig Gen"\n'
        )

        result = scan_custom_instruments(instruments_dir, _BASE_MAP)
        assert result["My Sig Gen"].is_builtin is False

    def test_custom_extending_type_absent_from_map_is_skipped(self, tmp_path):
        """A custom class whose base is not in the supplied map is skipped."""
        instruments_dir = tmp_path / "instruments"
        instruments_dir.mkdir()
        (instruments_dir / "__init__.py").write_text("")
        (instruments_dir / "my_sig_gen.py").write_text(
            "from visa_vulture.instruments import SignalGenerator\n"
            "\n"
            "class MySigGen(SignalGenerator):\n"
            '    display_name = "My Sig Gen"\n'
        )

        # Base map contains only PowerSupply — the SG-derived custom is skipped.
        ps_only_map = {PowerSupply: "power_supply"}
        result = scan_custom_instruments(instruments_dir, ps_only_map)
        assert result == {}


class TestBuiltinEntriesFlag:
    def test_builtin_entries_marked_is_builtin(self):
        registry = build_instrument_registry(_BUILTINS)
        assert registry["Power Supply"].is_builtin is True
        assert registry["Signal Generator"].is_builtin is True


# === Tests for equipment model integration ===


class TestEquipmentModelCustomClass:
    def test_connect_with_custom_class(self, equipment_model, mock_visa_connection):
        """Custom class parameter creates the custom instrument."""
        equipment_model.connect_instrument(
            "TCPIP::1.2.3.4::INSTR",
            "signal_generator",
            instrument_class=FakeSignalGen,
        )
        assert isinstance(equipment_model.instrument, FakeSignalGen)
        assert isinstance(equipment_model.instrument, SignalGenerator)
        assert equipment_model.instrument_type == "signal_generator"

    def test_connect_without_custom_class_uses_default(
        self, equipment_model, mock_visa_connection
    ):
        """Without custom class, default instrument is used."""
        equipment_model.connect_instrument(
            "TCPIP::1.2.3.4::INSTR",
            "signal_generator",
        )
        assert type(equipment_model.instrument) is SignalGenerator
        assert equipment_model.instrument_type == "signal_generator"
