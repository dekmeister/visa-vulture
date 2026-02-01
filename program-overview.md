# VISAvulture - Program Overview

## Purpose

A Python GUI application for controlling test equipment over VISA. The application loads test plans from CSV files, executes them against connected instruments, and provides real-time feedback through logging and plotting.

## Architecture: Model-View-Presenter (MVP)

### Why MVP?

- **Testability:** Model can be tested without GUI; presenter can be tested with mock view
- **Separation of concerns:** Business logic isolated from display logic
- **Maintainability:** Changes to GUI don't affect instrument control logic
- **Extensibility:** New views (e.g., CLI) could be added without changing model

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Model                            │
│  • Equipment state machine (UNKNOWN/IDLE/RUNNING/ERROR) │
│  • Test plan representation                             │
│  • Instrument abstraction                               │
│  • No knowledge of GUI                                  │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ method calls, callbacks
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Presenter                          │
│  • Coordinates model and view                           │
│  • Manages background threads for VISA communication    │
│  • Translates user actions to model operations          │
│  • Translates model state to view updates               │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ user events, display updates
                          ▼
┌─────────────────────────────────────────────────────────┐
│                         View                            │
│  • Tkinter widgets                                      │
│  • Log panel with filtering                             │
│  • Plot panel for real-time data                        │
│  • Exposes callbacks, no business logic                 │
└─────────────────────────────────────────────────────────┘
```

## State Machine

The equipment state machine is intentionally simple to start:

```
UNKNOWN  ──►  IDLE  ──►  RUNNING  ──►  IDLE
    │           │            │
    ▼           ▼            ▼
  ERROR       ERROR        ERROR
```

| State   | Description                                      |
|---------|--------------------------------------------------|
| UNKNOWN | Default startup state; equipment state unknown   |
| IDLE    | Connected and ready; not executing a test        |
| RUNNING | Actively executing a test plan                   |
| ERROR   | Failure occurred; user intervention required     |

## Key Design Decisions

### 1. Simulation Support via PyVISA-sim

- Allows development and testing without hardware
- Application code unchanged between real and simulated modes
- Controlled by configuration flag

### 2. Configuration Validation

- JSON configuration file for instruments and settings
- All validation errors reported before application starts
- Clear error messages guide user to fix issues

### 3. Logging as First-Class Feature

- Python standard logging library
- Dual output: file (persistent) and GUI panel (visible)
- Filterable by level in the GUI
- Captures instrument communication, state changes, user actions

### 4. Threading for Responsiveness

- VISA operations run in background threads
- GUI remains responsive during long operations
- Thread-safe queue for passing results back to main thread

### 5. Test Plans as CSV

- Simple, editable format for test sequences
- Required `# instrument_type` metadata comment at the top of the file specifies the plan type
- Other metadata comments starting with # for various additional functions (e.g. modulation)
- Data columns vary by instrument type:
  - Power supply: duration, voltage, current columns
  - Signal generator: duration, frequency, power columns
- Each step specifies a duration (how long it lasts); absolute times are computed automatically
- Validated on load with clear error reporting

## Technology Stack

| Component        | Technology                    |
|------------------|-------------------------------|
| GUI Framework    | Tkinter (ttk for modern look) |
| Plotting         | Matplotlib (embedded)         |
| Instrument Comms | PyVISA                        |
| Simulation       | PyVISA-sim                    |
| Logging          | Python logging module         |
| Configuration    | JSON                          |
| Test Plans       | CSV                           |

## Extensibility Points

| Future Need                  | How Structure Supports It              |
|------------------------------|----------------------------------------|
| Additional instruments       | Add new class in instruments/          |
| New test plan types          | Add TestStep subclass in model/test_plan.py, parser in file_io/ |
| More states                  | Extend EquipmentState enum             |
| New file formats             | Add parser in file_io/                 |
| Parallel instrument control  | Extend threading_helpers               |
| Alternative UI               | New view implementation, same model    |
| Additional presenter logic   | Extract to focused presenter classes   |
