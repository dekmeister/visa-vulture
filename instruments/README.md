# Custom Instruments

This directory contains user-defined instrument extensions for VISA Vulture.

## How It Works

VISA Vulture auto-scans this directory at startup. Any Python module containing a class that extends one of the built-in instrument types (`PowerSupply` or `SignalGenerator`) and defines a `display_name` class attribute will be discovered and added to the Resource Manager dialog's instrument type dropdown.

Custom instruments inherit all functionality from their parent type and work with existing test plans. They are registered against the *same* built-in type as their parent — they do **not** create a new instrument type.

## Rules

1. Custom instruments **must** extend a built-in instrument type — `PowerSupply` or `SignalGenerator` (from `visa_vulture.instruments`)
2. Custom instruments **must not** extend `BaseInstrument` directly. Instrument *types* are defined only by the in-package `INSTRUMENT_TYPE_REGISTRY` (`visa_vulture/model/instrument_types.py`); this directory can only add variants of existing types, not new ones
3. Custom instruments **must** define a `display_name` class attribute (this appears in the UI dropdown)
4. One class per module is recommended for clarity

## Creating a Custom Instrument

1. Create a new Python file in this directory (e.g., `my_instrument.py`)
2. Import the parent class from `visa_vulture.instruments`
3. Create a class that extends it and defines `display_name`
4. Add any instrument-specific methods

### Minimal Example

```python
from visa_vulture.instruments import SignalGenerator

class MySignalGen(SignalGenerator):
    display_name = "My Custom Signal Gen"
```

### Full Example

See [psg_e8257d.py](psg_e8257d.py) for a complete example extending `SignalGenerator` for the Keysight PSG E8257D.

## Limitations

- Custom methods are **not called** during test plan execution. The step executor for the parent type uses the standard parent interface (e.g., `set_frequency`, `set_power` for signal generators).
- Custom instruments cannot define new instrument types, columns, plot axes, or test-plan formats — those come from the type's descriptor in `INSTRUMENT_TYPE_REGISTRY`. To add a genuinely new type, see CLAUDE.md ("Adding a New Instrument Type").
- Custom methods are available when using visa-vulture as a library for direct instrument control.
