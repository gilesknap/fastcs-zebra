[![CI](https://github.com/DiamondLightSource/fastcs-zebra/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/fastcs-zebra/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/fastcs-zebra/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/fastcs-zebra)
[![PyPI](https://img.shields.io/pypi/v/fastcs-zebra.svg)](https://pypi.org/project/fastcs-zebra)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# fastcs_zebra

FastCS driver for Diamond Light Source Zebra position compare and logic hardware.

This driver provides EPICS PVs to control and monitor the Zebra hardware through
a modern asyncio-based Python implementation using the FastCS framework. It communicates
directly with the Zebra via serial port (115200 baud ASCII protocol), replacing the
legacy AreaDetector/Asyn-based driver.

Source          | <https://github.com/DiamondLightSource/fastcs-zebra>
:---:           | :---:
PyPI            | `pip install fastcs-zebra`
Docker          | `docker run ghcr.io/diamondlightsource/fastcs-zebra:latest`
Documentation   | <https://diamondlightsource.github.io/fastcs-zebra>
Releases        | <https://github.com/DiamondLightSource/fastcs-zebra/releases>

## Quick Start

### Running the EPICS IOC

```bash
# Install
pip install fastcs-zebra

# Start the EPICS server
python -m fastcs_zebra --port /dev/ttyUSB0 --pv-prefix BL99I-EA-ZEBRA-01

# Or for a simulation zebra
python -m fastcs_zebra --port sim://zebra01 --pv-prefix TEST-ZEB

# Generate a Phoebus screen file
python -m fastcs_zebra --port /dev/ttyUSB0 \
    --pv-prefix BL99I-EA-ZEBRA-01: \
    --gui zebra.bob
```

### Testing with EPICS Tools

```bash
# Check connection
caget BL99I-EA-ZEBRA-01:CONNECTED

# Read firmware version
caget BL99I-EA-ZEBRA-01:SYS_VER

# Set soft inputs
caput BL99I-EA-ZEBRA-01:SOFT_IN 5

# Arm position compare
caput BL99I-EA-ZEBRA-01:PC_ARM 1

# Monitor captured data
camonitor BL99I-EA-ZEBRA-01:PC_ENC1_LAST
```

### Using the Python API

```python
from fastcs_zebra import ZebraTransport, ZebraProtocol

async with ZebraTransport("/dev/ttyUSB0") as transport:
    protocol = ZebraProtocol(transport)

    # Read firmware version
    version = await protocol.read_register(0xF0)
    print(f"Firmware: {version:#06x}")

    # Write soft inputs
    await protocol.write_register(0x7F, 0x05)

    # Read 32-bit register
    captures = await protocol.read_register_32bit(0xF6, 0xF7)
    print(f"Captures: {captures}")
```

## Features

- **Async Serial Communication**: Non-blocking I/O using aioserial
- **EPICS Integration**: Automatic PV creation via FastCS framework
- **Position Compare**: Interrupt-driven capture of encoder positions
- **Complete Protocol**: All Zebra serial commands supported (R/W/S/L)
- **Modern Python**: Type hints, asyncio, dataclasses

## Current Implementation Status

✅ **Phase 1 Complete**: Serial communication layer
- ZebraTransport: Asyncio serial I/O
- ZebraProtocol: Register read/write, flash commands
- InterruptHandler: Position compare data parsing
- CLI: Interactive testing tool

🚧 **Phase 2 In Progress**: FastCS EPICS integration
- ZebraController: Basic PVs for testing Phase 1 functionality
- EPICS IOC entry point

⏳ **Phase 3 Planned**: Complete register abstraction and PV mapping
⏳ **Phase 4 Planned**: Full controller hierarchy
⏳ **Phase 5 Planned**: Motor integration and position compare arrays

<!-- README only content. Anything below this line won't be included in index.md -->

See https://diamondlightsource.github.io/fastcs-zebra for more detailed documentation.
