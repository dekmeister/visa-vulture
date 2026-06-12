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
├── view_specs.py                # Neutral leaf: pure-data view specs (no model/view imports)
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
│   ├── equipment.py             # Connection + state + StepContext impl; delegates run loop
│   ├── test_runner.py           # Stateless run_plan() + execute_steps()
│   ├── test_plan.py             # Generic only: TestStep, TestPlan
│   └── instrument_types/        # One module per type + generic framework
│       ├── __init__.py          # Public re-exports
│       ├── executor.py          # StepContext, StepExecutor, MetadataParser
│       ├── fields.py            # StepFieldSpec, SoftLimitSpec, column helpers
│       ├── descriptor.py        # InstrumentTypeDescriptor + consistency check
│       ├── power_supply.py      # Power-supply type (step, fields, executor, view, descriptor)
│       ├── signal_generator.py  # Signal-generator type + modulation metadata parsers
│       └── registry.py          # _BUILTIN_DESCRIPTORS, INSTRUMENT_TYPE_REGISTRY, validate_soft_limit_config
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
│   ├── modulation.py            # ModulationType/Config, AM/FM configs (driver-owned)
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
| `view_specs.py` | Neutral leaf module of pure-data view-presentation dataclasses (`ColumnSpec`, `AxisConfig`, `InstrumentViewSpec`, formatter aliases). Imports neither `model` nor `view`, so both may import it. Parsing-side field specs live in `model/instrument_types/fields.py` |

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
| `__init__.py` | Exports: `EquipmentModel`, `EquipmentState`, `INSTRUMENT_TYPE_REGISTRY`, `InstrumentTypeDescriptor`, `StepExecutor`, `StepContext`, `MetadataParser`, `validate_soft_limit_config`, `TestPlan`, `TestStep`, step subclasses, `INSTRUMENT_TYPE_*` constants (modulation classes now live in `instruments`) |
| `state_machine.py` | `EquipmentState` enum, transition validation, callback registration |
| `equipment.py` | `EquipmentModel` class coordinating state, instruments, connection; implements `StepContext` and delegates the run loop to `test_runner` |
| `test_runner.py` | Stateless `run_plan()` (descriptor lookup, instrument check, setup → loop → teardown) and `execute_steps()` (the generic per-step loop). Never imports `equipment` |
| `test_plan.py` | Generic only: `TestPlan` container and `TestStep` base class |
| `instrument_types/` | Subpackage: one module per instrument type plus the generic framework. `executor.py` (`StepContext`/`StepExecutor`/`MetadataParser`), `fields.py` (`StepFieldSpec`/`SoftLimitSpec`/column helpers), `descriptor.py` (`InstrumentTypeDescriptor` + consistency check), `power_supply.py` and `signal_generator.py` (each: constant, step dataclass, fields, executor, view spec, descriptor; SG also holds modulation metadata parsers), `registry.py` (`_BUILTIN_DESCRIPTORS`, `INSTRUMENT_TYPE_REGISTRY`, `validate_soft_limit_config`). `__init__.py` re-exports the public surface |

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
| `__init__.py` | Exports: `VISAConnection`, `PowerSupply`, `SignalGenerator`, modulation classes, loader functions |
| `visa_connection.py` | `VISAConnection` class managing ResourceManager, resource discovery |
| `base_instrument.py` | `BaseInstrument` abstract class with common interface and SCPI commands |
| `power_supply.py` | `PowerSupply` class with voltage/current control commands |
| `signal_generator.py` | `SignalGenerator` class with frequency/power control commands; imports modulation configs from sibling `modulation.py` |
| `modulation.py` | `ModulationType`, `ModulationConfig`, `AMModulationConfig`, `FMModulationConfig` — driver-owned (they parameterise the SG driver). Stdlib-only |
| `instrument_loader.py` | Auto-scanning, catalog building (`build_instrument_catalog`), and custom instrument loading |

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
    PowerSupplyTestStep, SignalGeneratorTestStep,
    INSTRUMENT_TYPE_POWER_SUPPLY, INSTRUMENT_TYPE_SIGNAL_GENERATOR,
)
from .test_plan import TestPlan, TestStep
# Modulation classes now live in visa_vulture.instruments (driver-owned).

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
from .modulation import (
    ModulationType, ModulationConfig, AMModulationConfig, FMModulationConfig,
)
from .instrument_loader import (
    InstrumentEntry, scan_custom_instruments,
    build_instrument_catalog, create_instrument,
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
