# GitHub Copilot Instructions for FastCS-Zebra Project

## Project Context

This project implements a FastCS driver for the Diamond Light Source Zebra position compare and logic control hardware. It replaces the legacy AreaDetector/Asyn-based driver with a modern FastCS implementation that communicates directly with the Zebra hardware over serial.

## Current Status (December 2025)

**Phase 1: COMPLETE ✅**
- Serial communication layer fully implemented using `aioserial`
- All modules have zero linting errors and follow modern Python patterns
- Completed modules:
  - `src/fastcs_zebra/transport.py` - ZebraTransport with asyncio serial I/O
  - `src/fastcs_zebra/protocol.py` - ZebraProtocol for register R/W and flash commands
  - `src/fastcs_zebra/interrupts.py` - InterruptHandler for position compare data parsing
  - `src/fastcs_zebra/cli.py` - Interactive CLI for hardware testing

**FastCS Integration: INITIAL IMPLEMENTATION ✅**
- Basic EPICS IOC is functional and ready for hardware testing
- Dependencies: `fastcs[epics]` provides both CA (Channel Access) and PVA (Process Variable Access) transports
- Testing: Uses `epicscorelibs` for CA client testing and `p4p` for PVA client testing
- Completed:
  - `src/fastcs_zebra/zebra_controller.py` - ZebraController with essential PVs
  - `src/fastcs_zebra/__main__.py` - EPICS IOC entry point with FastCS launcher
  - `docs/tutorials/epics-integration.md` - Complete EPICS usage guide
  - `tests/test_epics_integration.py` - Pytest-based EPICS integration tests for CA and PVA
  - Updated README.md with FastCS/EPICS focus
  - Updated `pyproject.toml` to include `fastcs[epics]` dependency for EPICS transport support
- Current PV Set (for testing Phase 1 functionality):
  - Connection status, firmware version, system state/error
  - Position compare control (encoder selection, prescaler, arm/disarm)
  - Soft inputs (read-write testing)
  - Last captured values (interrupt-driven updates)
  - Flash save/load, system reset commands

**Next Steps:**
- Test with real Zebra hardware via EPICS
- Expand PV coverage based on testing results
- Begin Phase 2: Complete register abstraction
- Phase 3: Full controller hierarchy (logic gates, pulse generators, etc.)
- Phase 4: Motor integration
- Phase 5: Position compare waveform arrays

## Current Goal

The immediate goal is to validate the Phase 1 serial communication layer and basic EPICS integration with real hardware. Once validated, we will:
- Add complete register abstraction layer
- Build full FastCS controller hierarchy matching the legacy EPICS interface
- Implement motor integration and position scaling
- Add position compare waveform data arrays
- Achieve full backward compatibility with legacy AreaDetector driver

## Dependencies

- **aioserial**: Asyncio-compatible serial I/O library for non-blocking serial communication
- **fastcs[epics]**: FastCS framework with EPICS transport extras
  - Provides CA (Channel Access) transport via `fastcs.transport.epics.ca`
  - Provides PVA (Process Variable Access) transport via `fastcs.transport.epics.pva`
  - Required for EPICS IOC functionality (`python -m fastcs_zebra`)
- **epicscorelibs** (dev): EPICS Channel Access client library for testing
- **p4p** (dev): EPICS PVAccess client library for testing

## Key Documentation

### Zebra Hardware Specifications
These specifications document the complete Zebra serial protocol and EPICS PV interface from the legacy driver:

- **Serial Protocol Specification**: [SERIAL_PROTOCOL_SPEC.md](https://github.com/DiamondLightSource/zebra/blob/fastcs-experiment/docs/SERIAL_PROTOCOL_SPEC.md)
  - Complete serial command set (read/write registers, flash operations, interrupts)
  - All 256 registers (0x00-0xFF) with addresses and types
  - 64-signal system bus routing matrix
  - Position compare interrupt protocol
  - Implementation guidelines and timing constraints

- **EPICS PV Interface Specification**: [EPICS_PV_SPEC.md](https://github.com/DiamondLightSource/zebra/blob/fastcs-experiment/docs/EPICS_PV_SPEC.md)
  - Complete PV naming conventions and patterns
  - Mapping of all PVs to serial protocol operations
  - Register access patterns (16-bit, 32-bit, mux, bitfield, prescaler)
  - Motor integration and position scaling
  - Position compare data arrays and filtering
  - AreaDetector integration requirements

### Legacy Implementation Reference
- **Original C++ Driver**: [zebraApp/src/zebra.cpp](https://github.com/DiamondLightSource/zebra/blob/fastcs-experiment/zebraApp/src/zebra.cpp)
- **Register Definitions**: [zebraApp/src/zebraRegs.h](https://github.com/DiamondLightSource/zebra/blob/fastcs-experiment/zebraApp/src/zebraRegs.h)
- **EPICS Database Template**: [zebraApp/Db/zebra.template](https://github.com/DiamondLightSource/zebra/blob/fastcs-experiment/zebraApp/Db/zebra.template)
- **Python Testing Tool**: [zebraApp/src/zebraTool.py](https://github.com/DiamondLightSource/zebra/blob/fastcs-experiment/zebraApp/src/zebraTool.py)

### FastCS Framework
- **FastCS Repository**: https://github.com/DiamondLightSource/FastCS
- **FastCS Documentation**: https://diamondlightsource.github.io/FastCS/

## Important Technical Details

### Serial Protocol
- **Baud Rate**: 115200, 8N1, no flow control
- **Line Terminator**: `\n` (newline, 0x0A)
- **Commands**: ASCII text (e.g., `R88` reads register 0x88, `W880003` writes 0x0003 to register 0x88)
- **Interrupts**: Asynchronous messages starting with `P` for position compare data
  - `PR` - Reset buffers (start of acquisition)
  - `P<TTTTTTTT><EEEEEEEE>...` - Timestamp and encoder/divider/sysbus data
  - `PX` - End of acquisition

### Register Architecture
- **256 registers** (0x00-0xFF), each 16-bit
- **32-bit values** use HI/LO register pairs (e.g., DIV1_DIVLO=0x38, DIV1_DIVHI=0x39)
- **Register types**: Read-write (regRW), Read-only (regRO), Command (regCmd), Multiplexer (regMux)
- **System Bus**: 64-signal routing matrix (indices 0-63) for connecting inputs, logic, and outputs

### Position Compare System
- Captures encoder positions, divider counts, and system bus state synchronized with motion
- Configurable via gate (start/width) and pulse (position/time interval) parameters
- Interrupt-driven data streaming with 32-bit timestamps
- Supports up to 10 simultaneous data streams (4 encoders, 2 system bus, 4 dividers)

## Implementation Strategy

### Phase 1: Serial Communication Layer ✅ COMPLETE
1. ✅ Serial port interface using `aioserial` (asyncio-compatible)
2. ✅ Request/response handling (R/W commands)
3. ✅ Interrupt message parsing (P messages)
4. ✅ Register read/write with verification (16-bit and 32-bit)
5. ✅ Flash storage commands (S/L)
6. ✅ Interactive CLI testing tool

**Files**: `transport.py`, `protocol.py`, `interrupts.py`, `cli.py`

### Phase 2: FastCS Integration ✅ INITIAL IMPLEMENTATION
1. ✅ Basic ZebraController with essential PVs
2. ✅ EPICS IOC entry point (`__main__.py`)
3. ✅ Interrupt monitoring background task
4. ✅ Connection lifecycle (connect/disconnect)
5. ✅ Documentation and test scripts

**Files**: `zebra_controller.py`, `__main__.py`, `docs/tutorials/epics-integration.md`

**Current PVs**:
- `CONNECTED`, `SYS_VER`, `SYS_STATERR` (read-only)
- `PC_ENC`, `PC_TSPRE`, `SOFT_IN` (read-write)
- `PC_NUM_CAP` (32-bit read-only)
- `PC_TIME_LAST`, `PC_ENC1-4_LAST` (interrupt updates)
- `STATUS_MSG` (status string)
- Commands: `PC_ARM`, `PC_DISARM`, `SAVE_TO_FLASH`, `LOAD_FROM_FLASH`, `SYS_RESET`

### Phase 3: Complete Register Abstraction ⏳ PLANNED
1. Create complete register definitions from zebraRegs.h
2. Implement system bus signal mapping (64-signal lookup)
3. Add comprehensive 32-bit register handling
4. Create type-specific register accessors (RW, RO, Mux, Cmd)
5. Build register name/address bidirectional lookup

### Phase 4: Full FastCS Controller Hierarchy ⏳ PLANNED
1. Design controller hierarchy matching hardware structure
2. Implement logic gates (AND1-4, OR1-4) as sub-controllers
3. Implement pulse generators (PULSE1-4) with delay/width/prescaler
4. Implement dividers (DIV1-4) with 32-bit divisor
5. Implement gate generators (GATE1-4)
6. Implement output routing (OUT1-8) with multiplexer selection
7. Implement complete position compare subsystem

### Phase 5: Motor Integration ⏳ PLANNED
1. Add motor record links for scaling (ERES, OFF)
2. Implement encoder position setting (POS1-4_SET)
3. Add position/time unit conversions
4. Handle motor direction and scaling multipliers

### Phase 6: Position Compare Data Arrays ⏳ PLANNED
1. Implement waveform data arrays (PC_TIME, PC_ENC1-4, PC_SYS1-2, PC_DIV1-4)
2. Add filtered system bus extraction (PC_FILT1-4)
3. Handle buffer management and rollover
4. Add NDArray support for AreaDetector compatibility (if required)

## Documentation Standards

- **Always use clickable links**: When referencing files in markdown documentation (`.md`, `.py`, `.cpp`, `.h`, `.template`, etc.), always format them as clickable links using markdown link syntax
- Use relative paths from the current file's location (e.g., `../` to go up a directory from `.github/`)
- This makes navigation easier in the GitHub web UI

## Code Style

- Follow FastCS patterns and conventions
- Use type hints throughout (modern Python 3.10+ syntax: `X | None` instead of `Optional[X]`)
- Comprehensive docstrings for public APIs
- Unit tests for all components
- Integration tests with zebra simulator
- Zero linting errors (enforced by Ruff)
- Line length ≤88 characters

## Testing

### Hardware Testing Procedure
```bash
# Install with EPICS support (if not already installed)
pip install -e ".[epics]"  # or: pip install fastcs[epics]

# Start the EPICS IOC
python -m fastcs_zebra --port /dev/ttyUSB0 --pv-prefix TEST:ZEBRA: --log-level DEBUG

# In another terminal, run EPICS integration tests (pytest)
pytest tests/test_epics_integration.py -v --prefix TEST:ZEBRA:

# Or use EPICS command-line tools for manual testing
caget TEST:ZEBRA:CONNECTED
caget TEST:ZEBRA:SYS_VER
caput TEST:ZEBRA:SOFT_IN 5
caput TEST:ZEBRA:PC_ARM 1
camonitor TEST:ZEBRA:PC_ENC1_LAST
```

### CLI Testing (without EPICS)
```bash
# CLI tool only requires aioserial, not fastcs[epics]
python -m fastcs_zebra.cli /dev/ttyUSB0
# Interactive commands: r, w, r32, w32, save, load, arm, disarm
```

## Key Implementation Notes

- **Asyncio Required**: All serial I/O must be non-blocking using `aioserial`
- **Type Checking**: Use `# type: ignore` for aioserial imports (optional dependency in stubs)
- **FastCS Patterns**:
  - Attributes: `AttrR` (read-only), `AttrW` (write-only), `AttrRW` (read-write)
  - Handlers: `handler=async_function` for reads, `handler_get`/`handler_put` for RW
  - Commands: `@command()` decorator for single-shot operations
  - Sub-controllers: `self.add_sub_controller("name", SubController())`
  - Lifecycle: Implement `async connect()` and `async disconnect()`
- **Interrupt Handling**: Background asyncio task monitors serial port for `P` messages
- **Register I/O**: All register operations go through `ZebraProtocol` methods
- **Error Handling**: Parse Zebra error responses (E0, E1R, E1W) and raise appropriate exceptions
