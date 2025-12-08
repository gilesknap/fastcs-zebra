# GitHub Copilot Instructions for FastCS-Zebra Project

## Project Context

This project implements a FastCS driver for the Diamond Light Source Zebra position compare and logic control hardware. It replaces the legacy AreaDetector/Asyn-based driver with a modern FastCS implementation that communicates directly with the Zebra hardware over serial.

## Current Goal

Implement a complete FastCS driver that:
- Connects directly to Zebra hardware via serial port (115200 baud, ASCII protocol)
- Exposes EPICS PVs matching the legacy interface for backward compatibility
- Removes dependencies on AreaDetector and Asyn
- Provides clean, maintainable Python code following FastCS patterns

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

### Phase 1: Serial Communication Layer
1. Implement serial port interface using asyncio-compatible library (e.g., `pyserial-asyncio` or `aioserial`)
   - **Important**: FastCS uses asyncio, so serial communication must be non-blocking
2. Create request/response handling (R/W commands)
3. Add interrupt message parsing (P messages)
4. Implement register read/write with verification

### Phase 2: Register Abstraction
1. Create register definitions from zebraRegs.h
2. Implement system bus signal mapping
3. Add 32-bit register handling (HI/LO pairs)
4. Create type-specific register accessors (RW, RO, Mux, etc.)

### Phase 3: FastCS Controller
1. Design controller hierarchy matching hardware structure
2. Implement logic gates (AND1-4, OR1-4)
3. Implement pulse generators (PULSE1-4)
4. Implement dividers (DIV1-4)
5. Implement gate generators (GATE1-4)
6. Implement output routing (OUT1-8)
7. Implement position compare subsystem

### Phase 4: Motor Integration
1. Add motor record links for scaling
2. Implement encoder position setting
3. Add position/time unit conversions

### Phase 5: Position Compare Data
1. Implement interrupt handler thread
2. Add waveform data arrays
3. Implement filtered system bus extraction
4. Add NDArray support for AreaDetector compatibility (if required)

## Documentation Standards

- **Always use clickable links**: When referencing files in markdown documentation (`.md`, `.py`, `.cpp`, `.h`, `.template`, etc.), always format them as clickable links using markdown link syntax
- Use relative paths from the current file's location (e.g., `../` to go up a directory from `.github/`)
- This makes navigation easier in the GitHub web UI

## Code Style

- Follow FastCS patterns and conventions
- Use type hints throughout
- Comprehensive docstrings for public APIs
- Unit tests for all components
- Integration tests with zebra simulator
