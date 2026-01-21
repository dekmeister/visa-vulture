# Equipment Controller - Implementation Plan

## Phase 1: Foundation

**Goal:** Basic application structure that runs and loads configuration.

### 1.1 Project Setup
- [ ] Create directory structure
- [ ] Set up virtual environment
- [ ] Create requirements.txt with dependencies
- [ ] Create empty `__init__.py` files for all packages

### 1.2 Configuration System
- [ ] Define config schema in `config/schema.py`
- [ ] Implement JSON loader in `config/loader.py`
- [ ] Create `default_config.json`
- [ ] Implement validation with comprehensive error accumulation
- [ ] Test: malformed JSON, missing fields, invalid values

### 1.3 Logging Setup
- [ ] Implement `logging_config/setup.py`
- [ ] Configure file handler with rotation
- [ ] Create custom handler for GUI (placeholder until view exists)
- [ ] Test: verify logs write to file correctly

### 1.4 Basic Main Entry Point
- [ ] Implement `main.py` skeleton
- [ ] Load and validate config (exit on errors)
- [ ] Initialise logging
- [ ] Create root Tk window
- [ ] Verify application starts and exits cleanly

---

## Phase 2: Instrument Layer

**Goal:** VISA communication working with simulation support.

### 2.1 VISA Connection Management
- [ ] Implement `instruments/visa_connection.py`
- [ ] Resource manager creation (real and sim backends)
- [ ] Resource discovery (`list_available_resources()`)
- [ ] Test: verify sim backend loads correctly

### 2.2 Base Instrument
- [ ] Implement `instruments/base_instrument.py`
- [ ] Define abstract interface: connect, disconnect, query, write
- [ ] Implement common SCPI commands (*IDN?, *RST)
- [ ] Connection state tracking (is_connected property)

### 2.3 Concrete Instrument
- [ ] Implement `instruments/power_supply.py`
- [ ] Instrument-specific commands
- [ ] Inherit/use base instrument behaviour

### 2.4 Simulation Configuration
- [ ] Create `simulation/instruments.yaml`
- [ ] Define simulated responses for power supply
- [ ] Test: connect to simulated instrument, query *IDN?

---

## Phase 3: Model Layer

**Goal:** Business logic independent of GUI.

### 3.1 State Machine
- [ ] Implement `model/state_machine.py`
- [ ] EquipmentState enum (UNKNOWN, IDLE, RUNNING, ERROR)
- [ ] Transition validation logic
- [ ] Callback registration for state changes

### 3.2 Test Plan
- [ ] Implement `model/test_plan.py`
- [ ] TestPlan dataclass (steps with time, frequency, power)
- [ ] TestStep dataclass for individual steps

### 3.3 Test Plan Reader
- [ ] Implement `file_io/test_plan_reader.py`
- [ ] CSV parsing with column validation
- [ ] Error accumulation for invalid data
- [ ] Return TestPlan object or list of errors

### 3.4 Equipment Model
- [ ] Implement `model/equipment.py`
- [ ] Hold instrument references and current state
- [ ] Methods: scan_resources, connect, disconnect
- [ ] Methods: load_test_plan, run_test, stop
- [ ] State transition calls
- [ ] Test: state transitions work correctly

---

## Phase 4: View Layer

**Goal:** GUI displays information and captures user input.

### 4.1 Main Window Structure
- [ ] Implement `view/main_window.py`
- [ ] Create frame layout (file section, controls, status)
- [ ] Expose callback hooks for presenter
- [ ] Methods to update display elements

### 4.2 Log Panel
- [ ] Implement `view/log_panel.py`
- [ ] Scrolling text display
- [ ] Auto-scroll to newest entries
- [ ] Level filter dropdown (DEBUG/INFO/WARNING/ERROR)
- [ ] Custom logging handler that emits to panel

### 4.3 Plot Panel
- [ ] Implement `view/plot_panel.py`
- [ ] Embed matplotlib figure
- [ ] Method to update plot with new data
- [ ] Basic styling and axis labels

### 4.4 Integrate Panels
- [ ] Assemble panels in main_window.py
- [ ] Verify layout displays correctly
- [ ] Test: manual interaction with widgets

---

## Phase 5: Presenter & Integration

**Goal:** Wire everything together into working application.

### 5.1 Threading Helpers
- [ ] Implement `utils/threading_helpers.py`
- [ ] BackgroundTaskRunner class
- [ ] Queue-based result passing
- [ ] Polling mechanism for Tkinter integration

### 5.2 Equipment Presenter
- [ ] Implement `presenter/equipment_presenter.py`
- [ ] Wire view callbacks to handler methods
- [ ] Register for model state changes
- [ ] Implement background task execution for VISA operations
- [ ] Update view based on model state

### 5.3 Complete Main.py
- [ ] Instantiate all components
- [ ] Wire presenter to model and view
- [ ] Connect logging GUI handler to log panel
- [ ] Implement clean shutdown handling

### 5.4 Integration Testing
- [ ] Test: load config, start application
- [ ] Test: scan for simulated instruments
- [ ] Test: connect to simulated instrument
- [ ] Test: load test plan CSV
- [ ] Test: run test plan (simulated)
- [ ] Test: verify logs appear in panel
- [ ] Test: verify state transitions update UI

---

## Phase 6: Polish & Documentation

**Goal:** Production-ready application.

### 6.1 Error Handling
- [ ] Ensure all errors surface to user appropriately
- [ ] Add error state recovery (return to IDLE)
- [ ] Graceful handling of unexpected disconnection

### 6.2 UI Refinement
- [ ] Button enable/disable based on state
- [ ] Status indicators for connection state
- [ ] Consistent styling throughout

### 6.3 Documentation
- [ ] README with setup instructions
- [ ] Configuration file documentation
- [ ] Test plan CSV format documentation
- [ ] Simulation setup guide

### 6.4 Testing with Real Hardware
- [ ] Verify with actual instrument
- [ ] Adjust timing if needed
- [ ] Document any hardware-specific quirks

---

## Estimated Effort

| Phase | Description              | Relative Effort |
|-------|--------------------------|-----------------|
| 1     | Foundation               | Small           |
| 2     | Instrument Layer         | Medium          |
| 3     | Model Layer              | Medium          |
| 4     | View Layer               | Medium          |
| 5     | Presenter & Integration  | Large           |
| 6     | Polish & Documentation   | Small           |

## Dependencies Between Phases

```
Phase 1 (Foundation)
    │
    ├──► Phase 2 (Instruments)
    │         │
    │         ▼
    │    Phase 3 (Model) ◄─── requires instruments
    │
    └──► Phase 4 (View) ◄─── can parallel with 2 & 3
              │
              ▼
         Phase 5 (Integration) ◄─── requires all above
              │
              ▼
         Phase 6 (Polish)
```

Phases 2, 3, and 4 can be developed somewhat in parallel once Phase 1 is complete.
