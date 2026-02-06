"""
Custom instrument extensions for VISA Vulture.

Place custom instrument modules in this directory. Custom instruments must
extend PowerSupply or SignalGenerator from the visa_vulture package
(not BaseInstrument directly).

Each custom instrument class must define a `display_name` class attribute
which will appear in the Resource Manager dialog's instrument type dropdown.

Example:
    from visa_vulture.instruments import SignalGenerator

    class MySignalGen(SignalGenerator):
        display_name = "My Custom Signal Gen"

See instruments/README.md for full documentation and the psg_e8257d.py
file for a complete example.
"""
