# Zebra EPICS PV Interface Specification

## Overview

This document specifies the EPICS Process Variable (PV) interface for the Zebra hardware control system. It describes how EPICS PVs map to the underlying serial protocol commands and register operations detailed in [Zebra Serial Protocol Specification](serial-protocol.md).

IMPORTANT: this document describes the original AreaDetector Zebra Driver which uses an ALL_CAPS PV naming conventions. The FastCS Zebra driver implements the same PV interface for compatibility except that FastCS uses PascalCase.

The interface uses standard EPICS record types and follows Diamond Light Source conventions for naming and structure. All PVs use the naming pattern `$(P)$(Q):RECORD_NAME` where `$(P)` is the device prefix and `$(Q)` is the device suffix.

---

## Connection and System Status

### Connection Status

| PV Name | Record Type | Direction | Description | Serial Protocol Mapping |
|---------|-------------|-----------|-------------|------------------------|
| `$(P)$(Q):CONNECTED` | bi | Read | Connection status to Zebra hardware | Derived from successful serial I/O |
| `$(P)$(Q):INITIAL_POLL_DONE` | bi | Read | Initial register poll completed | Internal driver state after reading all configuration registers |
| `$(P)$(Q):SYS_VER` | ai | Read | Firmware version | Register 0xF0 (`SYS_VER`) via `R F0` command |
| `$(P)$(Q):SYS_STATERR` | ai | Read | System state/error flags | Register 0xF1 (`SYS_STATERR`) via `R F1` command |

**CONNECTED PV Values:**
- `0` (Not Connected) - No communication with Zebra
- `1` (Connected) - Active communication established

**INITIAL_POLL_DONE PV Values:**
- `0` (No) - Still reading initial register values
- `1` (Yes) - Complete set of register values available, safe to save configuration

---

## Configuration Management

### Flash Storage

| PV Name | Record Type | Direction | Description | Serial Protocol Mapping |
|---------|-------------|-----------|-------------|------------------------|
| `$(P)$(Q):STORE` | ao | Write | Save configuration to flash | `S` command |
| `$(P)$(Q):RESTORE` | ao | Write | Restore configuration from flash | `L` command |

**Usage:** Write any value to trigger the flash operation.

### File-Based Configuration

| PV Name | Record Type | Direction | Description | Serial Protocol Mapping |
|---------|-------------|-----------|-------------|------------------------|
| `$(P)$(Q):CONFIG_FILE` | waveform (CHAR) | Write | Filename for config read/write | Local file path (INI format) |
| `$(P)$(Q):CONFIG_READ` | ao | Write | Read config from file | Sends `W<AA><VVVV>` for each register in file |
| `$(P)$(Q):CONFIG_WRITE` | ao | Write | Write config to file | Sends `R<AA>` for all registers, saves to INI file |
| `$(P)$(Q):CONFIG_STATUS` | waveform (CHAR) | Read | Status message for file operations | Internal driver status string |

**Config File Format:** INI format with `[regs]` section containing `REGISTER_NAME = value` entries.

**Write Process:** Four-phase operation:
1. Send all write commands
2. Receive write acknowledgments
3. Send read commands for verification
4. Verify readback values match requested values

### System Reset

| PV Name | Record Type | Direction | Description | Serial Protocol Mapping |
|---------|-------------|-----------|-------------|------------------------|
| `$(P)$(Q):SYS_RESET` | ao | Write | Reset Zebra system | Register 0x7E (`SYS_RESET`) via `W 7E 0001` command |

**Effect:** Resets Zebra hardware, stops acquisition, clears position compare buffers.

---

## System Bus

The System Bus is a 64-signal routing matrix. Status and configuration PVs provide access to this bus.

### System Bus Status (Read-Only)

| PV Name | Record Type | Description | Serial Protocol Mapping |
|---------|-------------|-------------|------------------------|
| `$(P)$(Q):SYS_BUS1` | waveform (CHAR) | Key for system bus signals 0-31 | Static lookup table |
| `$(P)$(Q):SYS_BUS2` | waveform (CHAR) | Key for system bus signals 32-63 | Static lookup table |
| `$(P)$(Q):SYS_STAT1LO` | ai | System bus status bits 0-15 | Register 0xF2 (`SYS_STAT1LO`) |
| `$(P)$(Q):SYS_STAT1HI` | ai | System bus status bits 16-31 | Register 0xF3 (`SYS_STAT1HI`) |
| `$(P)$(Q):SYS_STAT1` | calc | System bus status 0-31 (32-bit) | `(STAT1HI << 16) \| STAT1LO` |
| `$(P)$(Q):SYS_STAT2LO` | ai | System bus status bits 32-47 | Register 0xF4 (`SYS_STAT2LO`) |
| `$(P)$(Q):SYS_STAT2HI` | ai | System bus status bits 48-63 | Register 0xF5 (`SYS_STAT2HI`) |
| `$(P)$(Q):SYS_STAT2` | calc | System bus status 32-63 (32-bit) | `(STAT2HI << 16) \| STAT2LO` |

**System Bus Signals (0-63):** See [Zebra Serial Protocol Specification](serial-protocol.md) for complete signal list including inputs (IN1-8), logic gates (AND1-4, OR1-4), pulse generators (PULSE1-4), etc.

---

## Register Access Patterns

The Zebra driver uses several standardized EPICS database templates to handle different register types. Each pattern creates a set of PVs with specific naming conventions.

### Standard 16-bit Register Pattern

**PVs Created:**
- `$(P)$(Q):PARAM` - ao - Demand value
- `$(P)$(Q):PARAM:RBV` - ai - Readback value
- `$(P)$(Q):PARAM:SET` - ao - Internal write record
- `$(P)$(Q):PARAM:SYNC` - calcout - Synchronization logic

**Serial Protocol Mapping:**
- Write: `W<AA><VVVV>` where AA is register address, VVVV is scaled 16-bit value
- Read: `R<AA>` to verify, triggered automatically after write

**Scaling:** Some registers use `ASLO` (analog slope) for unit conversion:
- Time values: `ASLO = 0.0001` (converts to milliseconds)
- Position values: Scaled by motor resolution (MRES)

**Examples:**
- `$(P)$(Q):PULSE1_DLY` - Pulse 1 delay (register 0x44, scaled to ms)
- `$(P)$(Q):PULSE1_WID` - Pulse 1 width (register 0x48, scaled to ms)

---

### Multiplexer (Mux) Register Pattern

Used for registers that select from the 64-signal system bus.

**PVs Created:**
- `$(P)$(Q):PARAM` - ao - Demand value (0-63)
- `$(P)$(Q):PARAM:RBV` - ai - Readback value (0-63)
- `$(P)$(Q):PARAM:STR` - stringin - Human-readable signal name
- `$(P)$(Q):PARAM:STA` - calcout - Current status of selected signal
- `$(P)$(Q):PARAM:SET` - ao - Internal write record

**Serial Protocol Mapping:**
- Write: `W<AA><VVVV>` where VVVV is system bus index (0-63)
- Read: `R<AA>` returns index, driver translates to signal name
- Status: Extracts bit from `SYS_STAT1/2` based on selected index

**Drive Limits:** DRVL=0, DRVH=63 (valid system bus indices)

**Examples:**
- `$(P)$(Q):AND1_INP1` - AND gate 1 input 1 (register 0x08)
- `$(P)$(Q):OUT1_TTL` - Output 1 TTL routing (register 0x60)

**Signal Name Translation:**
- Write: User can write index or name
- Read: `:RBV` shows index, `:STR` shows name (e.g., "IN1_TTL")

---

### 32-bit Register Pattern

Used for registers that require 32-bit values (HI/LO pairs) and motor position scaling.

**PVs Created:**
- `$(P)$(Q):PARAM` - ao - Demand value in engineering units (EGU)
- `$(P)$(Q):PARAM:RBV` - calcout - Readback in EGU
- `$(P)$(Q):PARAM:RBV_CTS` - ai - Readback in raw counts
- `$(P)$(Q):PARAM:SET` - ao - Internal write record
- `$(P)$(Q):PARAM:CALC` - calcout - Convert EGU to counts

**Serial Protocol Mapping:**
- Write: Two commands:
  1. `W<AALO><VVVVLO>` - Write low 16 bits
  2. `W<AAHI><VVVVHI>` - Write high 16 bits
- Read: `R<AALO>` and `R<AAHI>`, driver combines to 32-bit value
- Driver parameter: `PARAMHILO` (virtual 32-bit register)

**Motor Scaling:**
- `ERES` (encoder resolution) from linked motor record
- `OFF` (offset) from linked motor record
- Formula: `counts = (EGU_value - OFF) / ERES`
- Reverse: `EGU_value = counts * ERES + OFF`

**Examples:**
- `$(P)$(Q):PC_GATE_START` - Gate start position (registers 0x8E/0x8F)
- `$(P)$(Q):PC_PULSE_STEP` - Pulse step size (registers 0x9B/0x9C)
- `$(P)$(Q):DIV1_DIV` - Divider 1 divisor (registers 0x38/0x39)

---

### Bitfield Register Pattern

Used for registers where each bit is a separate boolean control.

**PVs Created:** (for each bit 0-15)
- `$(P)$(Q):PARAM:B0` through `$(P)$(Q):PARAM:BF` - bo - Individual bit controls
- `$(P)$(Q):PARAM:RBV` - ai - Full register readback
- `$(P)$(Q):PARAM:SYNCB0` through `$(P)$(Q):PARAM:SYNCBF` - calcout - Bit extraction

**Serial Protocol Mapping:**
- Write: `W<AA><VVVV>` where VVVV is composed from all 16 bits
- Read: `R<AA>`, driver extracts each bit via shifts
- Bit N value = `(register_value >> N) & 1`

**Examples:**
- `$(P)$(Q):AND1_ENA:B0-B3` - Enable bits for AND1 inputs 1-4 (register 0x04)
- `$(P)$(Q):PC_BIT_CAP:B0-B9` - Position compare capture selection (register 0x9F)

---

### Prescaler Register Pattern

Special pattern for time prescaler registers.

**PVs Created:**
- `$(P)$(Q):PARAM` - mbbo - Multi-bit binary output (enum selection)
- `$(P)$(Q):PARAM:RBV` - mbbi - Multi-bit binary input (enum readback)

**Enum Values:**
- `0: "10s"` - Prescaler = 500000, time units = 10 seconds
- `1: "s"` - Prescaler = 5000, time units = seconds
- `2: "ms"` - Prescaler = 5, time units = milliseconds

**Serial Protocol Mapping:**
- Write: `W<AA><VVVV>` where VVVV is prescaler value
- Conversion: User selects enum, driver writes corresponding prescaler value

**Examples:**
- `$(P)$(Q):PC_TSPRE` - Position compare timestamp prescaler (register 0x89)
- `$(P)$(Q):PULSE1_PRE` - Pulse 1 prescaler (register 0x4C)

---

## Logic Gates

### AND Gates (AND1-AND4)

Each AND gate has identical PV structure. Example for AND1:

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):AND1_ENA:B0-B3` | bo | Enable each of 4 inputs | 0x04 | `W 04 <bits>` |
| `$(P)$(Q):AND1_INV:B0-B3` | bo | Invert each of 4 inputs | 0x00 | `W 00 <bits>` |
| `$(P)$(Q):AND1_INP1` | ao/mux | Input 1 source (0-63) | 0x08 | `W 08 <index>` |
| `$(P)$(Q):AND1_INP2` | ao/mux | Input 2 source (0-63) | 0x09 | `W 09 <index>` |
| `$(P)$(Q):AND1_INP3` | ao/mux | Input 3 source (0-63) | 0x0A | `W 0A <index>` |
| `$(P)$(Q):AND1_INP4` | ao/mux | Input 4 source (0-63) | 0x0B | `W 0B <index>` |
| `$(P)$(Q):AND1_OUT` | calcout | Current output state | SYS_STAT2 bit 0 | Extracted from `R F4` |

**Logic:** Output = (INP1 ⊕ INV:B0) AND (INP2 ⊕ INV:B1) AND (INP3 ⊕ INV:B2) AND (INP4 ⊕ INV:B3)
- Only enabled inputs (ENA:Bn = 1) contribute to AND operation
- XOR with invert bit allows active-low inputs

**System Bus Index:** AND1=32, AND2=33, AND3=34, AND4=35

**Replicated For:** AND1 (0x00-0x0B), AND2 (0x0C-0x17), AND3 (0x10-0x13), AND4 (0x14-0x17)

---

### OR Gates (OR1-OR4)

Structure identical to AND gates but with OR logic. Example for OR1:

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):OR1_ENA:B0-B3` | bo | Enable each of 4 inputs | 0x1C | `W 1C <bits>` |
| `$(P)$(Q):OR1_INV:B0-B3` | bo | Invert each of 4 inputs | 0x18 | `W 18 <bits>` |
| `$(P)$(Q):OR1_INP1-4` | ao/mux | Input sources | 0x20-0x23 | `W 20-23 <index>` |
| `$(P)$(Q):OR1_OUT` | calcout | Current output state | SYS_STAT2 bit 4 | Extracted from `R F4` |

**System Bus Index:** OR1=36, OR2=37, OR3=38, OR4=39

---

## Gate Generators (GATE1-GATE4)

Gate generators create gated outputs with trigger and reset inputs. Example for GATE1:

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):GATE1_INP1` | ao/mux | Trigger input (0-63) | 0x30 | `W 30 <index>` |
| `$(P)$(Q):GATE1_INP2` | ao/mux | Reset input (0-63) | 0x34 | `W 34 <index>` |
| `$(P)$(Q):GATE1_OUT` | calcout | Current output state | SYS_STAT2 bit 8 | Extracted from `R F4` |

**Behavior:**
- Rising edge on INP1 sets output high
- Rising edge on INP2 resets output low
- Classic SR latch topology

**System Bus Index:** GATE1=40, GATE2=41, GATE3=42, GATE4=43

---

## Pulse Dividers (DIV1-DIV4)

Frequency dividers with 32-bit divisor. Example for DIV1:

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):DIV1_INP` | ao/mux | Input source (0-63) | 0x40 | `W 40 <index>` |
| `$(P)$(Q):DIV1_DIV` | ao/32bit | Division factor (1-2^32) | 0x38/0x39 | `W 38 <LO>`, `W 39 <HI>` |
| `$(P)$(Q):DIV1_OUTD` | calcout | Divided output state | SYS_STAT2 bit 12 | Extracted from `R F4` |
| `$(P)$(Q):DIV1_OUTN` | calcout | Non-divided output state | SYS_STAT2 bit 16 | Extracted from `R F4` |

**Additional Control:**

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):DIV_FIRST:B0-B3` | bo | First pulse behavior for DIV1-4 | 0x7C | `W 7C <bits>` |

**System Bus Index:**
- DIV1_OUTD=44, DIV2_OUTD=45, DIV3_OUTD=46, DIV4_OUTD=47
- DIV1_OUTN=48, DIV2_OUTN=49, DIV3_OUTN=50, DIV4_OUTN=51

---

## Pulse Generators (PULSE1-PULSE4)

Programmable pulse generators with delay, width, and prescaler. Example for PULSE1:

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PULSE1_INP` | ao/mux | Trigger input (0-63) | 0x50 | `W 50 <index>` |
| `$(P)$(Q):PULSE1_DLY` | ao | Delay in ms | 0x44 | `W 44 <value/10000>` |
| `$(P)$(Q):PULSE1_WID` | ao | Width in ms | 0x48 | `W 48 <value/10000>` |
| `$(P)$(Q):PULSE1_PRE` | mbbo | Prescaler (10s/s/ms) | 0x4C | `W 4C <prescaler>` |
| `$(P)$(Q):PULSE1_OUT` | calcout | Current output state | SYS_STAT2 bit 20 | Extracted from `R F4` |

**Prescaler Values:** See Prescaler Register Pattern above.

**Additional Control:**

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):POLARITY:B0-B3` | bo | Output polarity for PULSE1-4 | 0x54 | `W 54 <bits>` |

**System Bus Index:** PULSE1=52, PULSE2=53, PULSE3=54, PULSE4=55

---

## Outputs (OUT1-OUT8)

Output routing multiplexers. Each output connector has multiple signal types.

### OUT1-OUT4 (Multi-signal Outputs)

| PV Pattern | Description | Registers | Example (OUT1) |
|------------|-------------|-----------|----------------|
| `$(P)$(Q):OUT1_TTL` | TTL output routing | 0x60-0x69 | `W 60 <index>` |
| `$(P)$(Q):OUT1_NIM` | NIM output routing | 0x61-0x6A | `W 61 <index>` |
| `$(P)$(Q):OUT1_LVDS` | LVDS output routing | 0x62-0x6B | `W 62 <index>` |

**OUT3 Special:** Has OC (open collector) instead of NIM

| PV | Register | Description |
|----|----------|-------------|
| `$(P)$(Q):OUT3_TTL` | 0x66 | TTL output |
| `$(P)$(Q):OUT3_OC` | 0x67 | Open collector output |
| `$(P)$(Q):OUT3_LVDS` | 0x68 | LVDS output |

**OUT4 Special:** Has PECL instead of LVDS

| PV | Register | Description |
|----|----------|-------------|
| `$(P)$(Q):OUT4_TTL` | 0x69 | TTL output |
| `$(P)$(Q):OUT4_NIM` | 0x6A | NIM output |
| `$(P)$(Q):OUT4_PECL` | 0x6B | PECL output |

### OUT5-OUT8 (Encoder Outputs)

Encoder emulation outputs with enable control.

| PV Pattern | Description | Registers | Example (OUT5) |
|------------|-------------|-----------|----------------|
| `$(P)$(Q):OUT5_ENCA` | A-phase signal routing | 0x6C-0x78 | `W 6C <index>` |
| `$(P)$(Q):OUT5_ENCB` | B-phase signal routing | 0x6D-0x79 | `W 6D <index>` |
| `$(P)$(Q):OUT5_ENCZ` | Z-phase (index) routing | 0x6E-0x7A | `W 6E <index>` |
| `$(P)$(Q):OUT5_CONN` | Enable output | 0x6F-0x7B | `W 6F <index>` |

**CONN Behavior:** When CONN input is high, encoder outputs are enabled; when low, outputs are tri-stated.

---

## Quadrature Encoder

Quadrature encoder generator from two input signals.

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):QUAD_STEP` | ao/mux | Step input source (0-63) | 0x56 | `W 56 <index>` |
| `$(P)$(Q):QUAD_DIR` | ao/mux | Direction input source (0-63) | 0x55 | `W 55 <index>` |
| `$(P)$(Q):QUAD_OUTA` | calcout | A-phase output state | SYS_STAT2 bit 24 | Extracted from `R F4` |
| `$(P)$(Q):QUAD_OUTB` | calcout | B-phase output state | SYS_STAT2 bit 25 | Extracted from `R F4` |

**System Bus Index:** QUAD_OUTA=56, QUAD_OUTB=57

**Behavior:** Generates quadrature signals from step/direction inputs.

---

## Soft Inputs

Software-controlled digital inputs accessible via system bus.

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):SOFT_IN` | ao | 4-bit control (bits 0-3) | 0x7F | `W 7F 000<value>` |

**Bit Mapping:**
- Bit 0 → SOFT_IN1 (system bus index 60)
- Bit 1 → SOFT_IN2 (system bus index 61)
- Bit 2 → SOFT_IN3 (system bus index 62)
- Bit 3 → SOFT_IN4 (system bus index 63)

**Usage:** Write decimal value 0-15 to set soft input states.

---

## Position Compare

Position compare subsystem for synchronized data capture during motion.

### Position Compare Arm/Disarm

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_ARM` | ao | Arm position compare | 0x8B | `W 8B 0001` → sends `PR` interrupt |
| `$(P)$(Q):PC_DISARM` | ao | Disarm position compare | 0x8C | `W 8C 0001` → sends `PX` interrupt |
| `$(P)$(Q):ARM_BUSY` | busy | Acquisition busy status | N/A | Set by PC_ARM, cleared by `PX` interrupt |
| `$(P)$(Q):PC_ARM_SEL` | mbbo | Arm source | 0x8A | `W 8A <value>` |
| `$(P)$(Q):PC_ARM_INP` | ao/mux | External arm input | 0x57 | `W 57 <index>` |

**PC_ARM_SEL Values:**
- `0: "Soft"` - Software arm via PC_ARM PV
- `1: "External"` - External signal via PC_ARM_INP

**Arm Sequence:**
1. User writes to PC_ARM
2. Driver sends `W 8B 0001`
3. Zebra responds `W8BOK`
4. Zebra sends `PR` interrupt
5. ARM_BUSY set to 1
6. Position compare data starts arriving

**Disarm Sequence:**
1. User writes to PC_DISARM (or automatically at end)
2. Zebra sends `PX` interrupt
3. ARM_BUSY cleared to 0

---

### Position Compare Encoder Selection

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_ENC` | mbbo | Encoder selection | 0x88 | `W 88 <value>` |

**PC_ENC Values:**
- `0: "Enc1"` - Use encoder 1
- `1: "Enc2"` - Use encoder 2
- `2: "Enc3"` - Use encoder 3
- `3: "Enc4"` - Use encoder 4
- `4: "Enc1+Enc2+Enc3+Enc4"` - Use sum of all encoders

---

### Position Compare Timestamp

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_TSPRE` | mbbo | Timestamp prescaler | 0x89 | `W 89 <prescaler>` |

**PC_TSPRE Values:** Same as prescaler pattern (10s/s/ms).

**Timestamp Calculation:**
- Raw timestamp from `P` message is 32-bit counter
- Time = (timestamp * 0.0001) time_units
- Rollover handling: Add 429496.7296 time_units when counter wraps

---

### Position Compare Gate

Controls when position compare events are captured.

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_GATE_SEL` | mbbo | Gate source | 0x8D | `W 8D <value>` |
| `$(P)$(Q):PC_GATE_INP` | ao/mux | External gate input | 0x58 | `W 58 <index>` |
| `$(P)$(Q):PC_GATE_START` | ao/32bit | Gate start position/time | 0x8E/0x8F | `W 8E <LO>`, `W 8F <HI>` |
| `$(P)$(Q):PC_GATE_WID` | ao/32bit | Gate width | 0x90/0x91 | `W 90 <LO>`, `W 91 <HI>` |
| `$(P)$(Q):PC_GATE_NGATE` | ao/32bit | Number of gates | 0x92/0x93 | `W 92 <LO>`, `W 93 <HI>` |
| `$(P)$(Q):PC_GATE_STEP` | ao/32bit | Step between gates | 0x94/0x95 | `W 94 <LO>`, `W 95 <HI>` |
| `$(P)$(Q):PC_GATE_OUT` | calcout | Gate output state | SYS_STAT1 bit 30 | Extracted from `R F3` |

**PC_GATE_SEL Values:**
- `0: "Position"` - Position-based gating (uses encoder value)
- `1: "Time"` - Time-based gating (uses timestamp counter)
- `2: "External"` - External signal via PC_GATE_INP

**Units:** START, WID, STEP are in encoder counts (position mode) or time units (time mode).

---

### Position Compare Pulse

Controls when capture pulses are generated.

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_PULSE_SEL` | mbbo | Pulse source | 0x96 | `W 96 <value>` |
| `$(P)$(Q):PC_PULSE_INP` | ao/mux | External pulse input | 0x59 | `W 59 <index>` |
| `$(P)$(Q):PC_PULSE_START` | ao/32bit | First pulse position/time | 0x97/0x98 | `W 97 <LO>`, `W 98 <HI>` |
| `$(P)$(Q):PC_PULSE_WID` | ao/32bit | Pulse width | 0x99/0x9A | `W 99 <LO>`, `W 9A <HI>` |
| `$(P)$(Q):PC_PULSE_STEP` | ao/32bit | Step between pulses | 0x9B/0x9C | `W 9B <LO>`, `W 9C <HI>` |
| `$(P)$(Q):PC_PULSE_MAX` | ao/32bit | Maximum pulses | 0x9D/0x9E | `W 9D <LO>`, `W 9E <HI>` |
| `$(P)$(Q):PC_PULSE_DLY` | ao/32bit | Pulse delay | 0xA1/0xA2 | `W A1 <LO>`, `W A2 <HI>` |
| `$(P)$(Q):PC_PULSE_OUT` | calcout | Pulse output state | SYS_STAT1 bit 31 | Extracted from `R F3` |

**PC_PULSE_SEL Values:** Same as PC_GATE_SEL (Position/Time/External).

---

### Position Compare Direction

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_DIR` | mbbo | Position compare direction | 0xA0 | `W A0 <value>` |

**PC_DIR Values:**
- `0: "Positive"` - Count up
- `1: "Negative"` - Count down

---

### Position Compare Capture Selection

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_BIT_CAP:B0-B9` | bo | Select data to capture | 0x9F | `W 9F <bits>` |

**Bit Mapping:**
- Bit 0: Encoder 1
- Bit 1: Encoder 2
- Bit 2: Encoder 3
- Bit 3: Encoder 4
- Bit 4: System Bus 1 (signals 0-31)
- Bit 5: System Bus 2 (signals 32-63)
- Bit 6: Divider 1 count
- Bit 7: Divider 2 count
- Bit 8: Divider 3 count
- Bit 9: Divider 4 count

**Effect on Interrupts:** Determines which `<EEEEEEEE>` fields appear in `P<TTTTTTTT>...` messages.

---

### Position Compare Captured Data

**Timestamp Array:**

| PV Name | Type | Description | Interrupt Message Mapping |
|---------|------|-------------|---------------------------|
| `$(P)$(Q):PC_TIME` | waveform (DOUBLE) | Timestamp array | `<TTTTTTTT>` field from each `P` message |

**Encoder/Data Arrays:**

| PV Name | Type | Description | Interrupt Message Mapping |
|---------|------|-------------|---------------------------|
| `$(P)$(Q):PC_ENC1` | waveform (DOUBLE) | Encoder 1 positions | 1st `<EEEEEEEE>` field (if bit 0 set) |
| `$(P)$(Q):PC_ENC2` | waveform (DOUBLE) | Encoder 2 positions | 2nd `<EEEEEEEE>` field (if bit 1 set) |
| `$(P)$(Q):PC_ENC3` | waveform (DOUBLE) | Encoder 3 positions | 3rd `<EEEEEEEE>` field (if bit 2 set) |
| `$(P)$(Q):PC_ENC4` | waveform (DOUBLE) | Encoder 4 positions | 4th `<EEEEEEEE>` field (if bit 3 set) |
| `$(P)$(Q):PC_SYS1` | waveform (DOUBLE) | System bus 1 state | 5th `<EEEEEEEE>` field (if bit 4 set) |
| `$(P)$(Q):PC_SYS2` | waveform (DOUBLE) | System bus 2 state | 6th `<EEEEEEEE>` field (if bit 5 set) |
| `$(P)$(Q):PC_DIV1` | waveform (DOUBLE) | Divider 1 count | 7th `<EEEEEEEE>` field (if bit 6 set) |
| `$(P)$(Q):PC_DIV2` | waveform (DOUBLE) | Divider 2 count | 8th `<EEEEEEEE>` field (if bit 7 set) |
| `$(P)$(Q):PC_DIV3` | waveform (DOUBLE) | Divider 3 count | 9th `<EEEEEEEE>` field (if bit 8 set) |
| `$(P)$(Q):PC_DIV4` | waveform (DOUBLE) | Divider 4 count | 10th `<EEEEEEEE>` field (if bit 9 set) |

**Last Values (Interrupt-Driven):**

| PV Name | Type | Description | Update Mechanism |
|---------|------|-------------|------------------|
| `$(P)$(Q):PC_ENC1_LAST` | ai | Last captured encoder 1 value | Updated on each `P` message |
| `$(P)$(Q):PC_ENC2_LAST` | ai | Last captured encoder 2 value | Updated on each `P` message |
| `$(P)$(Q):PC_ENC3_LAST` | ai | Last captured encoder 3 value | Updated on each `P` message |
| `$(P)$(Q):PC_ENC4_LAST` | ai | Last captured encoder 4 value | Updated on each `P` message |
| `$(P)$(Q):PC_SYS1_LAST` | ai | Last captured system bus 1 | Updated on each `P` message |
| `$(P)$(Q):PC_SYS2_LAST` | ai | Last captured system bus 2 | Updated on each `P` message |
| `$(P)$(Q):PC_DIV1_LAST` | ai | Last captured divider 1 count | Updated on each `P` message |
| `$(P)$(Q):PC_DIV2_LAST` | ai | Last captured divider 2 count | Updated on each `P` message |
| `$(P)$(Q):PC_DIV3_LAST` | ai | Last captured divider 3 count | Updated on each `P` message |
| `$(P)$(Q):PC_DIV4_LAST` | ai | Last captured divider 4 count | Updated on each `P` message |

**Filtered Arrays (System Bus Extraction):**

| PV Name | Type | Description | Processing |
|---------|------|-------------|------------|
| `$(P)$(Q):PC_FILT1` | waveform (CHAR) | Filtered bit from sys bus | Extracts single bit from PC_SYS1/2 |
| `$(P)$(Q):PC_FILT2` | waveform (CHAR) | Filtered bit from sys bus | Extracts single bit from PC_SYS1/2 |
| `$(P)$(Q):PC_FILT3` | waveform (CHAR) | Filtered bit from sys bus | Extracts single bit from PC_SYS1/2 |
| `$(P)$(Q):PC_FILT4` | waveform (CHAR) | Filtered bit from sys bus | Extracts single bit from PC_SYS1/2 |
| `$(P)$(Q):PC_FILTSEL1` | ao/mux | Select which bit to filter (0-63) | Index into system bus |
| `$(P)$(Q):PC_FILTSEL2` | ao/mux | Select which bit to filter (0-63) | Index into system bus |
| `$(P)$(Q):PC_FILTSEL3` | ao/mux | Select which bit to filter (0-63) | Index into system bus |
| `$(P)$(Q):PC_FILTSEL4` | ao/mux | Select which bit to filter (0-63) | Index into system bus |

**Filter Calculation:**
- If FILTSEL < 32: Source = PC_SYS1, bit = FILTSEL
- If FILTSEL >= 32: Source = PC_SYS2, bit = FILTSEL - 32
- For each array element: `FILT[i] = (Source[i] >> bit) & 1`

---

### Position Compare Status

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):PC_NUM_CAPLO` | ai | Captures count (low 16 bits) | 0xF6 | `R F6` |
| `$(P)$(Q):PC_NUM_CAPHI` | ai | Captures count (high 16 bits) | 0xF7 | `R F7` |
| `$(P)$(Q):PC_NUM_CAP` | calc | Total captures (32-bit) | Combined | `(HI << 16) \| LO` |
| `$(P)$(Q):PC_NUM_DOWN` | ai | Points downloaded to EPICS | N/A | Internal driver counter |

**PC_NUM_CAP:** Total position compare events generated by Zebra.
**PC_NUM_DOWN:** Number of data points processed and available in waveform PVs.

---

## Motor Integration

The Zebra driver integrates with EPICS motor records for position scaling.

### Motor Links

| PV Name | Type | Description |
|---------|------|-------------|
| `$(P)$(Q):M1` | stringin | Motor 1 PV name |
| `$(P)$(Q):M2` | stringin | Motor 2 PV name |
| `$(P)$(Q):M3` | stringin | Motor 3 PV name |
| `$(P)$(Q):M4` | stringin | Motor 4 PV name |
| `$(P)$(Q):M1:DESC` | stringin | Motor 1 description |
| `$(P)$(Q):M2:DESC` | stringin | Motor 2 description |
| `$(P)$(Q):M3:DESC` | stringin | Motor 3 description |
| `$(P)$(Q):M4:DESC` | stringin | Motor 4 description |
| `$(P)$(Q):M1:RBV` | ai | Motor 1 readback value |
| `$(P)$(Q):M2:RBV` | ai | Motor 2 readback value |
| `$(P)$(Q):M3:RBV` | ai | Motor 3 readback value |
| `$(P)$(Q):M4:RBV` | ai | Motor 4 readback value |

**Macros:**
- `M1`, `M2`, `M3`, `M4` - Motor PV prefixes (e.g., `BL99I-MO-STAGE-01:X`)
- `M1DIR`, `M2DIR`, `M3DIR`, `M4DIR` - Set to "-" if motor direction inverted
- `M1MULT`, `M2MULT`, `M3MULT`, `M4MULT` - Scaling multiplier for encoder decoding

### Motor Scaling Parameters

| PV Name | Type | Description | Source |
|---------|------|-------------|--------|
| `$(P)$(Q):M1:ERES` | ai | Encoder resolution (EGU/count) | From motor.MRES or .ERES |
| `$(P)$(Q):M1:OFF` | ai | Position offset (EGU) | From motor.OFF |
| `$(P)$(Q):M1:SCALE` | ao | Additional scale factor | Driver parameter, sent to asyn |
| `$(P)$(Q):M1:OFF:OUT` | ao | Offset output to driver | Driver parameter, sent to asyn |

**These exist for M1-M4 and are used in 32-bit register calculations.**

### Position Setting

| PV Name | Type | Description | Register | Serial Command |
|---------|------|-------------|----------|----------------|
| `$(P)$(Q):POS1_SET` | ao/32bit | Set encoder 1 position | 0x80/0x81 | `W 80 <LO>`, `W 81 <HI>` |
| `$(P)$(Q):POS2_SET` | ao/32bit | Set encoder 2 position | 0x82/0x83 | `W 82 <LO>`, `W 83 <HI>` |
| `$(P)$(Q):POS3_SET` | ao/32bit | Set encoder 3 position | 0x84/0x85 | `W 84 <LO>`, `W 85 <HI>` |
| `$(P)$(Q):POS4_SET` | ao/32bit | Set encoder 4 position | 0x86/0x87 | `W 86 <LO>`, `W 87 <HI>` |

**Usage:** Load Zebra encoder counter with current motor position (for position compare homing).

---

## AreaDetector Integration

The Zebra driver inherits from ADDriver to provide NDArray output for position compare data.

### AreaDetector PVs (Standard)

| PV Name | Type | Description |
|---------|------|-------------|
| `$(P)$(Q):Acquire` | bo | Start/stop acquisition |
| `$(P)$(Q):Acquire_RBV` | bi | Acquisition status readback |
| `$(P)$(Q):ArrayCounter` | longin | Array counter |
| `$(P)$(Q):ArrayCounter_RBV` | longin | Array counter readback |
| `$(P)$(Q):NumImages` | longout | Number of images to acquire |
| `$(P)$(Q):NumImagesCounter_RBV` | longin | Images acquired counter |
| `$(P)$(Q):ImageMode` | mbbo | Image mode (Single/Multiple/Continuous) |
| `$(P)$(Q):ArrayCallbacks` | bo | Enable array callbacks |

**Acquire Mapping:**
- `Acquire = 1` → Sends `W 8B 0001` (PC_ARM)
- `Acquire = 0` → Sends `W 8C 0001` (PC_DISARM)

**NDArray Structure:**
- Dimensions: `[NARRAYS+1, 1]` (11 columns, 1 row per pulse)
- Column 0: Timestamp
- Columns 1-10: Encoder/system bus/divider values (as configured by PC_BIT_CAP)
- Data Type: Float64
- Updated on each position compare interrupt

---

## Implementation Notes for FastCS Driver

### Register Polling Strategy

**Fast Polling (4 Hz):**
- `SYS_STATERR` (0xF1)
- `SYS_STAT1LO/HI` (0xF2/0xF3)
- `SYS_STAT2LO/HI` (0xF4/0xF5)
- `PC_NUM_CAPLO/HI` (0xF6/0xF7)

**Slow Polling (1 Hz):**
- All configuration registers (0x00-0xA2)
- Skip command-type registers (regCmd)

**On-Demand:**
- Read after write for verification
- Read during configuration file operations

### Interrupt Processing

**Message Classification:**
- Messages starting with `P` → Interrupt queue
- Messages starting with `R` or `W` → Response queue
- Messages starting with `S` or `L` → Response queue

**Interrupt Types:**
- `PR\n` → Reset buffers, set acquiring
- `P<hex data>\n` → Parse and store capture data
- `PX\n` → End acquisition, process final buffers

### Data Scaling

**Encoder Values:**
- Raw: Signed 32-bit integer from serial message
- Scaled: `value_egu = raw_value * ERES + OFF`

**System Bus Values:**
- Raw: Unsigned 32-bit integer from serial message
- Each bit represents state of one system bus signal

**Time Values:**
- Raw: Unsigned 32-bit counter
- Scaled: `time = raw * 0.0001 * time_unit + rollover_offset`

### PV Update Mechanism

**Interrupt-driven updates (SCAN = "I/O Intr"):**
- System status registers
- Position compare data arrays
- Last captured values
- Connection status

**Periodic updates:**
- Configuration register readbacks (via polling)
- ARRAY_UPDATE trigger (1 second scan)

**User-initiated updates:**
- Write to demand PV triggers write + readback
- Configuration file operations
- Flash save/restore

---

## PV Naming Convention Summary

```
$(P)$(Q):CATEGORY_ITEM[:SUFFIX]

Where:
  P = Device prefix (e.g., "BL99I-EA-ZEBRA-01")
  Q = Device suffix (e.g., ":")
  CATEGORY = Functional group (AND, OR, PULSE, PC, etc.)
  ITEM = Specific item (INP1, DLY, ENC1, etc.)
  SUFFIX = Optional qualifier:
    :RBV = Readback value
    :SET = Internal write record
    :STR = String representation
    :STA = Status
    :Bn = Bitfield bit n
    :SYNC = Synchronization record
    _LAST = Last interrupt value
```

**Examples:**
- `BL99I-EA-ZEBRA-01:PULSE1_DLY` - Pulse 1 delay demand
- `BL99I-EA-ZEBRA-01:PULSE1_DLY:RBV` - Pulse 1 delay readback
- `BL99I-EA-ZEBRA-01:AND1_INP1:STR` - AND1 input 1 source name
- `BL99I-EA-ZEBRA-01:PC_BIT_CAP:B0` - Position compare capture bit 0
- `BL99I-EA-ZEBRA-01:PC_ENC1_LAST` - Last captured encoder 1 value

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Auto-generated | Initial specification from zebra EPICS database templates |

---

## References

- Serial Protocol: [Zebra Serial Protocol Specification](serial-protocol.md)
- EPICS Templates: [Zebra EPICS Database Templates](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/Db/zebra.template) and sub-templates
- Driver Source: [Zebra Driver Source](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/src/zebra.cpp)
- Register Definitions: [Zebra Register Definitions](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/src/zebraRegs.h)
