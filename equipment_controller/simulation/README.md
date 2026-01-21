# Simulation Configuration

This directory contains PyVISA-sim configuration for development without hardware.

## instruments.yaml

Defines simulated instrument responses for:

- **Power Supply** (`TCPIP::192.168.1.100::INSTR`)
  - Identification: SimPower PS-1000
  - Voltage control (VOLT, VOLT?)
  - Current control (CURR, CURR?)
  - Output control (OUTP ON/OFF, OUTP?)

## Usage

Set `simulation_mode: true` in the configuration file to use these simulated instruments.

## Adding New Instruments

1. Add a new resource entry under `resources:` with the VISA address
2. Create a device definition under `devices:`
3. Define dialogues (fixed query/response pairs) and properties (stateful values)
4. See PyVISA-sim documentation for full syntax

## Limitations

- Simulated instruments return fixed or stateful values, not realistic measurements
- Timing is not simulated (operations complete instantly)
- Error conditions are not simulated beyond basic syntax
