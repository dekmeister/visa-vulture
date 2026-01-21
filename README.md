# Equipment Controller

A Python GUI application for controlling test equipment over VISA. Load test plans from CSV files, execute them against connected instruments, and monitor results through real-time logging and plotting.

## Features

- **VISA Instrument Control**: Connect to power supplies and other test equipment
- **Test Plan Execution**: Load CSV-based test plans with voltage/current sequences
- **Real-time Plotting**: Monitor voltage and current during test execution
- **Comprehensive Logging**: Filterable log panel with file output
- **Simulation Mode**: Develop and test without hardware using PyVISA-sim

## Requirements

- Python 3.10+
- Tkinter (usually included with Python)
- pyvisa >= 1.13.0
- pyvisa-sim >= 0.5.1
- matplotlib >= 3.7.0

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd visa-vulture
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
# Run with default configuration (simulation mode)
python run.py

# Run with simulation mode explicitly enabled
python run.py --simulation

# Run with custom configuration file
python run.py --config path/to/config.json
```

### Test Plan Format

Test plans are CSV files with the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| step | Yes | Step number (1-based, sequential) |
| time | Yes | Time in seconds when step starts |
| voltage | Yes | Voltage setpoint in volts |
| current | Yes | Current limit in amps |
| description | No | Optional step description |

Example (`test_plan.csv`):
```csv
step,time,voltage,current,description
1,0.0,5.0,1.0,Initial voltage
2,5.0,10.0,1.5,Ramp to 10V
3,10.0,12.0,2.0,Final voltage
4,15.0,0.0,0.0,Power down
```

### Configuration

Configuration is stored in JSON format. Key settings:

```json
{
    "simulation_mode": true,
    "log_level": "INFO",
    "instruments": [
        {
            "name": "Power Supply",
            "resource_address": "TCPIP::192.168.1.100::INSTR",
            "type": "power_supply",
            "timeout_ms": 5000
        }
    ]
}
```

See `equipment_controller/config/default_config.json` for full configuration options.

## Architecture

The application follows the Model-View-Presenter (MVP) pattern:

```
┌─────────────────────────────────────────────────────────┐
│                        Model                            │
│  • Equipment state machine (UNKNOWN/IDLE/RUNNING/ERROR) │
│  • Test plan representation                             │
│  • Instrument abstraction                               │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Presenter                          │
│  • Coordinates model and view                           │
│  • Manages background threads for VISA communication    │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                         View                            │
│  • Tkinter GUI components                               │
│  • Log panel, plot panel, controls                      │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
equipment_controller/
├── main.py                 # Entry point
├── config/                 # Configuration loading
├── model/                  # Business logic, state machine
├── view/                   # Tkinter GUI components
├── presenter/              # MVP coordination
├── file_io/                # CSV parsing, results writing
├── instruments/            # VISA instrument classes
├── logging_config/         # Logging setup
├── simulation/             # PyVISA-sim configuration
└── utils/                  # Threading helpers
```

## Adding New Instruments

1. Create a new class in `instruments/` inheriting from `BaseInstrument`
2. Implement required methods: `connect`, `disconnect`, `get_status`
3. Add instrument-specific commands
4. Register the type in `model/equipment.py`
5. Add simulation responses to `simulation/instruments.yaml`

## Development

### Running with Hardware

1. Set `simulation_mode: false` in configuration
2. Update instrument `resource_address` to match your equipment
3. Ensure VISA drivers are installed (NI-VISA, Keysight IO Libraries, etc.)

### Extending Simulation

Edit `equipment_controller/simulation/instruments.yaml` to add:
- New instrument responses
- Additional SCPI commands
- Stateful properties

## License

MIT License
