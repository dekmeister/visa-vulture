# VISA Vulture

A Python GUI application for controlling test equipment over VISA. Load test plans from CSV files, execute them against connected instruments, and monitor results through real-time logging and plotting.

## Features

- **VISA Instrument Control**: Connect to power supplies, signal generators, and other test equipment
- **Test Plan Execution**: Load CSV-based test plans for different instrument types
- **Real-time Plotting**: Monitor voltage/current or frequency/power during test execution
- **Test Points Table**: View all test plan steps in a tabular format
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

Test plans are CSV files. The format depends on the instrument type. Step numbers are assigned automatically based on row order.

#### Power Supply Test Plans

| Column | Required | Description |
|--------|----------|-------------|
| time | Yes | Time in seconds when step starts |
| voltage | Yes | Voltage setpoint in volts |
| current | Yes | Current limit in amps |
| description | No | Optional step description |

Example (`sample_test_plan.csv`):
```csv
time,voltage,current,description
0.0,5.0,1.0,Initial voltage
5.0,10.0,1.5,Ramp to 10V
10.0,12.0,2.0,Final voltage
15.0,0.0,0.0,Power down
```

#### Signal Generator Test Plans

| Column | Required | Description |
|--------|----------|-------------|
| type | Yes | Must be "signal_generator" |
| time | Yes | Time in seconds when step starts |
| frequency | Yes | Frequency in Hz |
| power | Yes | Power level in dBm |
| description | No | Optional step description |

Example (`sample_signal_generator_test_plan.csv`):
```csv
type,time,frequency,power,description
signal_generator,0.0,1000000,0,Start at 1 MHz
signal_generator,5.0,5000000,-5,Sweep to 5 MHz
signal_generator,10.0,10000000,-10,Peak at 10 MHz
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
        },
        {
            "name": "Signal Generator",
            "resource_address": "TCPIP::192.168.1.101::INSTR",
            "type": "signal_generator",
            "timeout_ms": 5000
        }
    ]
}
```

See `src/config/default_config.json` for full configuration options.

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
src/
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

Edit `src/simulation/instruments.yaml` to add:
- New instrument responses
- Additional SCPI commands
- Stateful properties

## License

MIT License
