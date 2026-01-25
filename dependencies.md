# VISA Vulture - Dependencies & Data Flow

## External Dependencies

Refer to requirements.txt

### Notes

| Package | Purpose | Notes |
|---------|---------|-------|
| pyvisa | VISA communication | Core instrument control |
| pyvisa-sim | Simulation backend | Development without hardware |
| matplotlib | Plotting | Embedded in Tkinter |
| tkinter | GUI framework | Included with Python (not in requirements.txt) |

---

## Internal Dependency Map

Arrows indicate "imports from" direction.

```
                                main.py
                                   │
          ┌────────────┬───────────┼───────────┬─────────────┐
          ▼            ▼           ▼           ▼             ▼
      config/    logging_config/  instruments/  model/       view/
                                       │          │            
                                       │          │            
                                       ▼          ▼            
                                    model/     file_io/       
                                                   │
                                                   ▼
                                                model/ (TestPlan, TestStep subclasses)


                              presenter/
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
              model/            view/           utils/
```

---

## Detailed Import Rules

### What Each Package Can Import

| Package | Can Import | Must NOT Import |
|---------|------------|-----------------|
| **main.py** | config, logging_config, instruments, model, view, presenter | file_io, utils (indirectly via others) |
| **config/** | (standard library only) | All internal packages |
| **logging_config/** | (standard library only) | All internal packages |
| **model/** | instruments, file_io | view, presenter, config, logging_config |
| **view/** | utils (optional) | model, presenter, instruments, file_io, config |
| **presenter/** | model, view, utils | instruments, file_io, config (go through model) |
| **file_io/** | model (TestPlan, TestStep subclasses, plan type constants) | view, presenter, instruments, config |
| **instruments/** | (pyvisa only) | All internal packages |
| **utils/** | (standard library only) | All internal packages |

---

## Data Flow Diagrams

### Startup Flow

```
main.py
   │
   ├─1─► config/loader.py ──► Load & validate JSON
   │         │
   │         ▼
   │     [Config dict or errors]
   │         │
   │     (exit if errors)
   │
   ├─2─► logging_config/setup.py ──► Configure handlers
   │
   ├─3─► instruments/ ──► Create instrument objects (disconnected)
   │
   ├─4─► model/ ──► Create EquipmentModel with instruments
   │
   ├─5─► view/ ──► Create MainWindow
   │
   ├─6─► presenter/ ──► Create EquipmentPresenter, wire callbacks
   │
   └─7─► root.mainloop() ──► Start GUI event loop
```

### User Action: Connect to Instrument

```
User clicks "Connect"
        │
        ▼
    MainWindow ──callback──► EquipmentPresenter
                                    │
                                    ▼
                            BackgroundTaskRunner
                                    │
                          (background thread)
                                    │
                                    ▼
                            EquipmentModel.connect()
                                    │
                                    ▼
                            PowerSupply.connect()
                                    │
                                    ▼
                            VISAConnection (pyvisa)
                                    │
                          (result via queue)
                                    │
                                    ▼
                            EquipmentPresenter
                                    │
                                    ▼
                            MainWindow.set_connection_status()
```

### User Action: Load Test Plan

```
User clicks "Load Test Plan"
        │
        ▼
    MainWindow ──callback──► EquipmentPresenter
                                    │
                                    ▼
                            file dialog (via view)
                                    │
                                    ▼
                            test_plan_reader.read_test_plan()
                                    │
                                    ▼
                            [TestPlan or errors]
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
                   (success)               (errors)
                        │                       │
                        ▼                       ▼
            EquipmentModel.load_test_plan()   MainWindow.show_error()
                        │
                        ▼
            MainWindow.display_test_plan()
```

### User Action: Run Test

```
User clicks "Run"
        │
        ▼
    MainWindow ──callback──► EquipmentPresenter
                                    │
                                    ▼
                            EquipmentModel.run_test()
                                    │
                                    ▼
                            State: IDLE → RUNNING
                                    │
                            (callback fires)
                                    │
                                    ▼
                            EquipmentPresenter._on_state_changed()
                                    │
                                    ▼
                            MainWindow.set_state_display("RUNNING")
                            MainWindow.set_buttons_enabled(...)
                                    │
                          (background thread)
                                    │
                            ┌───────┴───────┐
                            ▼               ▼
                    For each test step:   Log each action
                            │               │
                            ▼               ▼
                    PowerSupply.set_...   LogPanel updates
                            │
                            ▼
                    PlotPanel.update(data)
                            │
                    (test complete)
                            │
                            ▼
                    State: RUNNING → IDLE
```

### Logging Flow

```
Any component
      │
      │ logging.info("message")
      │
      ▼
  Root Logger
      │
      ├──────────────────┐
      ▼                  ▼
 FileHandler        GUILogHandler
      │                  │
      ▼                  ▼
 app.log file      LogPanel.append()
                         │
                         ▼
                   (filter by level)
                         │
                         ▼
                   Display in scrolling text
```

---

## State Change Propagation

```
EquipmentModel
      │
      │ _set_state(new_state)
      │
      ▼
  Notify registered callbacks
      │
      ▼
  EquipmentPresenter._on_state_changed()
      │
      │ (may be called from background thread)
      │
      ▼
  view.schedule(0, lambda: self._update_for_state(state))
      │
      │ (now on main thread)
      │
      ▼
  MainWindow.set_state_display()
  MainWindow.set_buttons_enabled()
```

---

## Thread Safety Boundaries

| Component | Thread | Notes |
|-----------|--------|-------|
| View (all) | Main thread only | Tkinter is not thread-safe |
| Presenter (callbacks from view) | Main thread | Button handlers |
| Presenter (queue polling) | Main thread | via `root.after()` |
| Model (state callbacks) | May be background | Must schedule GUI updates |
| Instruments | Background thread | VISA operations block |
| BackgroundTaskRunner | Manages workers | Results via queue |

**Rule:** Any code that touches Tkinter widgets must run on the main thread. Use `view.schedule()` to ensure this.

---

## Configuration Flow

```
default_config.json (shipped)
        │
        ▼
user_config.json (optional override)
        │
        ▼
    loader.py
        │
        ├──► schema.py (validate)
        │
        ▼
    [Config dict]
        │
        ▼
    main.py
        │
        ├──► simulation_mode? → VISAConnection backend selection
        │
        ├──► instruments config → Create instrument objects
        │
        └──► interface config → Window size, poll intervals
```
