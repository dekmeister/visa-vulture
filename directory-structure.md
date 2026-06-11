# VISA Vulture - Directory Structure

```
instruments/                    # User-defined custom instrument extensions (project root)
├── __init__.py
├── psg_e8257d.py               # Example: Keysight PSG E8257D signal generator
└── README.md

visa_vulture/
│
├── __init__.py
├── __main__.py
├── main.py
├── instrument_specs.py          # Neutral leaf: pure-data view/field specs (no model/view imports)
│
├── config/
│   ├── __init__.py
│   ├── loader.py
│   ├── schema.py
│   └── default_config.json
│
├── model/
│   ├── __init__.py
│   ├── state_machine.py
│   ├── equipment.py
│   ├── instrument_types.py      # Descriptor registry, step executors, built-in types
│   └── test_plan.py
│
├── view/
│   ├── __init__.py
│   ├── main_window.py
│   ├── log_panel.py
│   ├── plot_panel.py
│   ├── resource_manager_dialog.py
│   └── test_points_table.py
│
├── presenter/
│   ├── __init__.py
│   └── equipment_presenter.py
│
├── file_io/
│   ├── __init__.py
│   ├── test_plan_reader.py
│   └── results_writer.py
│
├── instruments/
│   ├── __init__.py
│   ├── visa_connection.py
│   ├── base_instrument.py
│   ├── power_supply.py
│   ├── signal_generator.py
│   └── instrument_loader.py
│
├── logging_config/
│   ├── __init__.py
│   └── setup.py
│
├── simulation/
│   ├── instruments.yaml
│   └── README.md
│
└── utils/
    ├── __init__.py
    └── threading_helpers.py
```

---

## File Descriptions

### Root Level

| File | Purpose |
|------|---------|
| `__init__.py` | Package init with `__version__` |
| `__main__.py` | Enables `python -m visa_vulture` |
| `main.py` | Application entry point; loads config, initialises logging, wires components, manages shutdown |
| `instrument_specs.py` | Neutral leaf module of pure-data spec dataclasses (`StepFieldSpec`, `ColumnSpec`, `AxisConfig`, `SoftLimitSpec`, `InstrumentViewSpec`) and column helpers. Imports neither `model` nor `view`, so both may import it |

---

### config/

Configuration loading and validation.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `load_config`, `AppConfig`, `ValidationLimits`, `CommonSoftLimits` |
| `loader.py` | Load JSON file, call validation, return config dict or errors |
| `schema.py` | Define expected structure, field types, defaults, validation rules. `ValidationLimits` holds `common` plus a generic `instrument_limits: dict[str, dict[str, float]]` keyed by instrument type |
| `default_config.json` | Default configuration shipped with application |

---

### model/

Business logic, independent of GUI.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `EquipmentModel`, `EquipmentState`, `INSTRUMENT_TYPE_REGISTRY`, `InstrumentTypeDescriptor`, `StepExecutor`, `StepContext`, `validate_soft_limit_config`, `TestPlan`, `TestStep`, step subclasses, `INSTRUMENT_TYPE_*` constants, modulation classes |
| `state_machine.py` | `EquipmentState` enum, transition validation, callback registration |
| `equipment.py` | `EquipmentModel` class coordinating state, instruments, registry-driven test execution |
| `instrument_types.py` | `INSTRUMENT_TYPE_REGISTRY` of `InstrumentTypeDescriptor`s, the `StepExecutor` ABC and built-in executors, built-in field/view specs, the import-time descriptor↔step consistency check, and `validate_soft_limit_config` |
| `test_plan.py` | `TestPlan` container, `TestStep` base class, `PowerSupplyTestStep` and `SignalGeneratorTestStep` subclasses, `INSTRUMENT_TYPE_*` constants |

---

### view/

GUI components, no business logic.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `MainWindow`, `PlotPanel`, `ResourceManagerDialog`, `TestPointsTable`, `DisclaimerDialog` |
| `main_window.py` | Main application window; builds one plot/table tab per `InstrumentViewSpec`, exposes a keyed view API (`get_plot_panel`/`get_table`/`show_tab_only`/…) |
| `log_panel.py` | `LogPanel` widget with scrolling text, level filtering, auto-scroll |
| `plot_panel.py` | Single generic `PlotPanel` configured at construction with primary/secondary `AxisConfig` for dual-axis matplotlib plots |
| `resource_manager_dialog.py` | `ResourceManagerDialog` for instrument connection with resource scanning and identification |
| `test_points_table.py` | Generic `TestPointsTable` driven by a `ColumnSpec` list; each column formats a step via its `value_fn` |

---

### presenter/

Coordination between model and view.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `EquipmentPresenter` |
| `equipment_presenter.py` | Wire callbacks, manage threads, translate between model and view |

---

### file_io/

File parsing and writing.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `read_test_plan`, `TestPlanResult` |
| `test_plan_reader.py` | Parse CSV into `TestPlan`, validate columns and values |

---

### instruments/ (project root)

User-defined custom instrument extensions. Auto-scanned at startup.

| File | Purpose |
|------|---------|
| `__init__.py` | Package init with extension documentation |
| `psg_e8257d.py` | Example: Keysight PSG E8257D extending `SignalGenerator` |
| `README.md` | Documentation for creating custom instruments |

---

### visa_vulture/instruments/

VISA communication and instrument abstraction.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `VISAConnection`, `PowerSupply`, `SignalGenerator`, loader functions |
| `visa_connection.py` | `VISAConnection` class managing ResourceManager, resource discovery |
| `base_instrument.py` | `BaseInstrument` abstract class with common interface and SCPI commands |
| `power_supply.py` | `PowerSupply` class with voltage/current control commands |
| `signal_generator.py` | `SignalGenerator` class with frequency/power control commands |
| `instrument_loader.py` | Auto-scanning, registry building, and custom instrument loading |

---

### logging_config/

Logging setup.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `setup_logging`, `GUILogHandler` |
| `setup.py` | Configure root logger, file handler, GUI handler |

---

### simulation/

PyVISA-sim configuration.

| File | Purpose |
|------|---------|
| `instruments.yaml` | Device definitions and simulated responses |
| `README.md` | Documentation for extending simulation |

---

### utils/

Shared utilities.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports: `BackgroundTaskRunner` |
| `threading_helpers.py` | `BackgroundTaskRunner` class for thread-safe async operations |

---

## Package Exports Summary

Each `__init__.py` curates what other packages import:

```python
# config/__init__.py
from .loader import load_config
from .schema import AppConfig, ValidationLimits, CommonSoftLimits

# model/__init__.py
from .state_machine import EquipmentState
from .equipment import EquipmentModel
from .instrument_types import (
    INSTRUMENT_TYPE_REGISTRY, InstrumentTypeDescriptor,
    StepContext, StepExecutor, MetadataParser, validate_soft_limit_config,
)
from .test_plan import (
    TestPlan, TestStep, PowerSupplyTestStep, SignalGeneratorTestStep,
    INSTRUMENT_TYPE_POWER_SUPPLY, INSTRUMENT_TYPE_SIGNAL_GENERATOR,
    ModulationType, ModulationConfig, AMModulationConfig, FMModulationConfig,
)

# view/__init__.py
from .disclaimer_dialog import DisclaimerDialog
from .main_window import MainWindow
from .plot_panel import PlotPanel
from .resource_manager_dialog import ResourceManagerDialog
from .test_points_table import TestPointsTable

# presenter/__init__.py
from .equipment_presenter import EquipmentPresenter

# file_io/__init__.py
from .test_plan_reader import read_test_plan, TestPlanResult

# instruments/__init__.py
from .visa_connection import VISAConnection
from .base_instrument import BaseInstrument
from .power_supply import PowerSupply
from .signal_generator import SignalGenerator
from .instrument_loader import (
    InstrumentEntry, scan_custom_instruments,
    build_instrument_registry, create_instrument,
)

# logging_config/__init__.py
from .setup import setup_logging, GUILogHandler

# utils/__init__.py
from .threading_helpers import BackgroundTaskRunner, TaskResult
```

This allows clean imports elsewhere:

```python
from model import EquipmentModel, EquipmentState
from view import MainWindow
from instruments import PowerSupply
```
