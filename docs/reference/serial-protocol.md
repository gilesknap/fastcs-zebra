# Zebra Serial Protocol Specification

## Overview

This document specifies the serial communication protocol used to control and monitor the Zebra.

## Connection Parameters

- **Baud Rate**: 115200
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None
- **Line Terminator**: `\n` (newline, 0x0A)

## Protocol Characteristics

- **Request-Response**: The protocol is primarily request-response based
- **Asynchronous Events**: The device can send unsolicited interrupt messages (position compare data)
- **Text-Based**: All commands and responses are ASCII text
- **Case-Sensitive**: Commands use uppercase letters and hexadecimal notation

## Command Format

All commands are terminated with a newline character (`\n`).

### 1. Read Register Command

**Format**: `R<AA>\n`

- `R` - Read command identifier
- `<AA>` - 2-digit hexadecimal register address (00-FF)

**Response**: `R<AA><VVVV>\n`

- `R<AA>` - Echo of register address
- `<VVVV>` - 4-digit hexadecimal value (0000-FFFF, representing 16-bit value)

**Example**:
```
Command:  R88\n
Response: R880003\n
```
This reads register 0x88 (PC_ENC) and receives value 0x0003.

**Error Response**: `E1R<AA>\n`
- Indicates the register address is invalid or cannot be read

---

### 2. Write Register Command

**Format**: `W<AA><VVVV>\n`

- `W` - Write command identifier
- `<AA>` - 2-digit hexadecimal register address (00-FF)
- `<VVVV>` - 4-digit hexadecimal value to write (0000-FFFF)

**Response**: `W<AA>OK\n`

- `W<AA>` - Echo of register address
- `OK` - Success indicator

**Example**:
```
Command:  W88001F\n
Response: W88OK\n
```
This writes value 0x001F to register 0x88 (PC_ENC).

**Error Response**: `E1W<AA>\n`
- Indicates the register address is invalid or cannot be written

**Note**: Read-only registers (type `regRO`) will reject write commands.

---

### 3. Flash Storage Commands

#### Save to Flash

**Format**: `S\n`

**Response**: `SOK\n`

**Purpose**: Saves the current register configuration to non-volatile flash memory.

**Note**: This command may take ~100ms to complete.

#### Load from Flash

**Format**: `L\n`

**Response**: `LOK\n`

**Purpose**: Restores register configuration from non-volatile flash memory.

---

### 4. Generic Error Response

**Format**: `E0\n`

**Purpose**: Indicates a malformed or unrecognized command.

---

## Interrupt Messages (Asynchronous)

The Zebra sends unsolicited messages when position compare events occur. These messages are distinguished by starting with the letter `P`.

### Position Compare Reset Message

**Format**: `PR\n`

**Meaning**: Position compare has been armed. The host should reset its data buffers and prepare to receive position compare data.

**Trigger**: Sent when register `PC_ARM` (0x8B) is written with value 1.

---

### Position Compare Data Message

**Format**: `P<TTTTTTTT>[<EEEEEEEE>]...\n`

- `P` - Interrupt message identifier
- `<TTTTTTTT>` - 8-digit hexadecimal timestamp (32-bit unsigned)
- `[<EEEEEEEE>]...` - Zero or more 8-digit hexadecimal encoder/data values (32-bit signed for encoders, unsigned for system bus)

**Timestamp Encoding**:
- The timestamp is a 32-bit counter incremented at (50MHz / prescaler)
- The prescaler is set via register `PC_TSPRE` (0x89)
  - Prescaler = 5: Each count = 0.1 µs (time units in 0.01 ms increments)
  - Prescaler = 5000: Each count = 100 µs (time units in 0.01 s increments)
- When the counter rolls over at 2^32, add 429496.7296 time units to maintain continuity

**Data Fields**:
The number and meaning of data fields depends on register `PC_BIT_CAP` (0x9F):
- Bit 0: Encoder 1 (signed 32-bit, encoder counts)
- Bit 1: Encoder 2 (signed 32-bit, encoder counts)
- Bit 2: Encoder 3 (signed 32-bit, encoder counts)
- Bit 3: Encoder 4 (signed 32-bit, encoder counts)
- Bit 4: System Bus 1 (unsigned 32-bit, bit field)
- Bit 5: System Bus 2 (unsigned 32-bit, bit field)
- Bit 6: Divider 1 output count (unsigned 32-bit)
- Bit 7: Divider 2 output count (unsigned 32-bit)
- Bit 8: Divider 3 output count (unsigned 32-bit)
- Bit 9: Divider 4 output count (unsigned 32-bit)

**Example**:
```
PC_BIT_CAP = 0x0013 (bits 0, 1, 4 set)
Message: P00012A3000001234FFFF5678AB000000\n

Parsed:
  Timestamp: 0x00012A30 (76336 * 0.0001 = 7.6336 time units)
  Encoder 1: 0x00001234 (4660 counts)
  Encoder 2: 0xFFFF5678 (-43400 counts, signed)
  Sys Bus 1: 0xAB000000 (bits 31, 29, 27, 25, 24 set)
```

---

### Position Compare Complete Message

**Format**: `PX\n`

**Meaning**: Position compare acquisition has completed. No more data will be sent.

**Trigger**: Sent when:
- Register `PC_DISARM` (0x8C) is written with value 1, OR
- The configured number of pulses has been generated and captured

---

## Register Map

The Zebra has a 256-byte register space (addresses 0x00-0xFF). Each register is 16 bits wide.

### Register Types

1. **regRW**: Read-Write register (configuration)
2. **regRO**: Read-Only register (status/version)
3. **regCmd**: Command register (write-only, triggers actions)
4. **regMux**: Multiplexer register (selects from system bus, see System Bus section)

### Key Register Categories

#### Logic Gates (AND/OR)
- `0x00-0x07`: AND gate 1-4 inversion and enable bits
- `0x08-0x17`: AND gate 1-4 inputs (4 inputs × 4 gates)
- `0x18-0x1F`: OR gate 1-4 inversion and enable bits
- `0x20-0x2F`: OR gate 1-4 inputs (4 inputs × 4 gates)

#### Gate Generator
- `0x30-0x33`: GATE 1-4 input 1 (trigger)
- `0x34-0x37`: GATE 1-4 input 2 (reset)

#### Pulse Dividers
- `0x38-0x3F`: DIV 1-4 divisor (LO/HI pairs for 32-bit values)
- `0x40-0x43`: DIV 1-4 input select

#### Pulse Generators
- `0x44-0x47`: PULSE 1-4 delay
- `0x48-0x4B`: PULSE 1-4 width
- `0x4C-0x4F`: PULSE 1-4 prescaler
- `0x50-0x53`: PULSE 1-4 input select
- `0x54`: POLARITY - Output polarity control

#### Quadrature Encoder
- `0x55`: QUAD_DIR - Direction input
- `0x56`: QUAD_STEP - Step input

#### Position Compare Control
- `0x57`: PC_ARM_INP - External arm input select
- `0x58`: PC_GATE_INP - External gate input select
- `0x59`: PC_PULSE_INP - External pulse input select

#### Output Multiplexers
- `0x60-0x7B`: Output channel routing (28 outputs × 1 register each)
  - OUT1-4: Multiple output types per connector (TTL, NIM, LVDS, PECL, OC)
  - OUT5-8: Encoder outputs (ENCA, ENCB, ENCZ, CONN enable)

#### System Control
- `0x7C`: DIV_FIRST - Select first pulse behavior for dividers
- `0x7E`: SYS_RESET - System reset command
- `0x7F`: SOFT_IN - Software input register (4 bits for SOFT_IN1-4)

#### Position Compare Parameters
- `0x80-0x87`: POS1-4 SET (LO/HI pairs) - Load encoder counters
- `0x88`: PC_ENC - Select which encoder to use for position compare
- `0x89`: PC_TSPRE - Timestamp clock prescaler (5=milliseconds, 5000=seconds)
- `0x8A`: PC_ARM_SEL - Arm input source (0=software, 1=external)
- `0x8B`: PC_ARM - Software arm command
- `0x8C`: PC_DISARM - Software disarm command
- `0x8D`: PC_GATE_SEL - Gate source (0=position, 1=time, 2=external)
- `0x8E-0x95`: PC_GATE parameters (START, WID, NGATE, STEP - all LO/HI pairs)
- `0x96`: PC_PULSE_SEL - Pulse source (0=position, 1=time, 2=external)
- `0x97-0x9E`: PC_PULSE parameters (START, WID, STEP, MAX - all LO/HI pairs)
- `0x9F`: PC_BIT_CAP - Bit mask for data capture (which encoders/divs/sysbus)
- `0xA0`: PC_DIR - Position compare direction
- `0xA1-0xA2`: PC_PULSE_DLY (LO/HI) - Pulse delay

#### Status Registers (Read-Only)
- `0xF0`: SYS_VER - Firmware version
- `0xF1`: SYS_STATERR - System state/error flags
- `0xF2-0xF3`: SYS_STAT1 (LO/HI) - System bus status bits 0-31
- `0xF4-0xF5`: SYS_STAT2 (LO/HI) - System bus status bits 32-63
- `0xF6-0xF7`: PC_NUM_CAP (LO/HI) - Number of position compare captures

**Note**: Registers with "LO/HI" pairs represent 32-bit values:
- LO register contains bits 0-15
- HI register contains bits 16-31
- Combined value = (HI << 16) | LO

---

## System Bus

The System Bus is a 64-signal routing matrix that connects inputs, logic gates, and outputs. Each signal has an index (0-63) and a name.

### System Bus Signal Index

| Index | Signal Name | Description |
|-------|-------------|-------------|
| 0 | DISCONNECT | No connection |
| 1-3 | IN1_TTL, IN1_NIM, IN1_LVDS | Input 1 variants |
| 4-6 | IN2_TTL, IN2_NIM, IN2_LVDS | Input 2 variants |
| 7-9 | IN3_TTL, IN3_OC, IN3_LVDS | Input 3 variants |
| 10-12 | IN4_TTL, IN4_CMP, IN4_PECL | Input 4 variants |
| 13-16 | IN5_ENCA/B/Z, IN5_CONN | Encoder input 5 |
| 17-20 | IN6_ENCA/B/Z, IN6_CONN | Encoder input 6 |
| 21-24 | IN7_ENCA/B/Z, IN7_CONN | Encoder input 7 |
| 25-28 | IN8_ENCA/B/Z, IN8_CONN | Encoder input 8 |
| 29-31 | PC_ARM, PC_GATE, PC_PULSE | Position compare signals |
| 32-35 | AND1, AND2, AND3, AND4 | AND gate outputs |
| 36-39 | OR1, OR2, OR3, OR4 | OR gate outputs |
| 40-43 | GATE1, GATE2, GATE3, GATE4 | Gate generator outputs |
| 44-47 | DIV1-4_OUTD | Divider outputs (divided) |
| 48-51 | DIV1-4_OUTN | Divider outputs (not divided) |
| 52-55 | PULSE1, PULSE2, PULSE3, PULSE4 | Pulse generator outputs |
| 56-57 | QUAD_OUTA, QUAD_OUTB | Quadrature encoder outputs |
| 58-59 | CLOCK_1KHZ, CLOCK_1MHZ | Internal clocks |
| 60-63 | SOFT_IN1, SOFT_IN2, SOFT_IN3, SOFT_IN4 | Software inputs |

### Using Multiplexer Registers

When writing to a `regMux` type register:
- Write the index (0-63) of the desired system bus signal
- Example: To route IN1_TTL to OUT1_TTL:
  - OUT1_TTL is register 0x60
  - IN1_TTL has system bus index 1
  - Command: `W600001\n`

### Reading System Bus Status

The current state of all 64 system bus signals can be read from registers:
- `SYS_STAT1LO` (0xF2): Bits 0-15 of signals 0-31
- `SYS_STAT1HI` (0xF3): Bits 16-31 of signals 0-31
- `SYS_STAT2LO` (0xF4): Bits 0-15 of signals 32-63
- `SYS_STAT2HI` (0xF5): Bits 16-31 of signals 32-63

To read signal N:
1. Determine register: `SYS_STAT1LO/HI` for N<32, `SYS_STAT2LO/HI` for N≥32
2. Determine bit offset: N % 16
3. Read register and check bit: `(value >> bit_offset) & 1`

---

## Typical Usage Sequences

### 1. Connect and Read Firmware Version

```
→ R F0
← R F0 0020
```
Firmware version is 0x0020.

### 2. Configure a Simple Logic Gate

Route IN1_TTL through AND1 gate to OUT1_TTL:
```
→ W08 0001    # AND1_INP1 = IN1_TTL (index 1)
← W08OK
→ W04 0001    # AND1_ENA = enable input 1 only
← W04OK
→ W00 0000    # AND1_INV = don't invert
← W00OK
→ W60 0020    # OUT1_TTL = AND1 (index 32)
← W60OK
```

### 3. Configure Position Compare Acquisition

Setup to capture encoder 1 position at 1kHz:
```
→ W8C 0001    # PC_DISARM (clear any previous state)
← W8COK
→ W9F 0001    # PC_BIT_CAP = bit 0 (capture encoder 1)
← W9FOK
→ W89 1388    # PC_TSPRE = 5000 (for seconds units)
← W89OK
→ W88 0000    # PC_ENC = 0 (use encoder 1)
← W88OK
→ W8D 0001    # PC_GATE_SEL = 1 (time-based gate)
← W8DOK
→ W8E 0000    # PC_GATE_STARTLO = 0
← W8EOK
→ W8F 0000    # PC_GATE_STARTHI = 0
← W8FOK
→ W90 03E8    # PC_GATE_WIDLO = 1000 (1 second at 1kHz)
← W90OK
→ W91 0000    # PC_GATE_WIDHI = 0
← W91OK
→ W96 0001    # PC_PULSE_SEL = 1 (time-based pulse)
← W96OK
→ W97 0000    # PC_PULSE_STARTLO = 0
← W97OK
→ W98 0000    # PC_PULSE_STARTHI = 0
← W98OK
→ W99 0001    # PC_PULSE_WIDLO = 1 (minimal width)
← W99OK
→ W9A 0000    # PC_PULSE_WIDHI = 0
← W9AOK
→ W9B 000A    # PC_PULSE_STEPLO = 10 (10ms between pulses = 100Hz)
← W9BOK
→ W9C 0000    # PC_PULSE_STEPHI = 0
← W9COK
→ W8B 0001    # PC_ARM (start acquisition)
← W8BOK
← PR          # Unsolicited: buffers reset
← P00000000 12345678   # Data: time=0, enc1=0x12345678
← P0000000A 12345680   # Data: time=10ms, enc1=0x12345680
...
← PX          # Unsolicited: acquisition complete
```

### 4. Poll Status Registers

Typical polling sequence for fast-changing values:
```
→ RF1         # Read SYS_STATERR
← RF1 0000
→ RF2         # Read SYS_STAT1LO
← RF2 00A3
→ RF3         # Read SYS_STAT1HI
← RF3 0000
→ RF4         # Read SYS_STAT2LO
← RF4 1200
→ RF5         # Read SYS_STAT2HI
← RF5 0001
→ RF6         # Read PC_NUM_CAPLO
← RF6 00C8
→ RF7         # Read PC_NUM_CAPHI
← RF7 0000
```
Result: 200 (0x00C8) position compare captures have occurred.

### 5. Save Configuration to Flash

```
→ S
← SOK
```

---

## Error Handling

### Timeouts
- If no response is received within a reasonable timeout (1-10 seconds), the connection may be lost
- The driver should attempt to reconnect or alert the user
- During flash operations (S, L), allow longer timeouts (~100-200ms)

### Error Responses
- `E0` - Malformed command: Check command syntax
- `E1R<AA>` - Read error: Register may not exist or is not readable
- `E1W<AA>` - Write error: Register may not exist, is read-only, or value is invalid

### Connection Loss Detection
- Failed writes or timeouts indicate disconnection
- Implementation should track connection state and notify when lost/restored

### Message Queue Overflow
- The host must process interrupt messages quickly to avoid buffer overflow
- If messages arrive faster than they can be processed, some may be dropped
- Implementation should use a sufficiently large queue (e.g., 10,000 messages)

---

## Implementation Considerations for FastCS Driver

### Threading Model
1. **Read Thread**: Continuously reads from serial port, dispatching messages to:
   - Response queue (for `R`, `W`, `S`, `L` responses)
   - Interrupt queue (for `P` messages)

2. **Poll Thread**: Periodically reads status registers (at ~4Hz recommended)
   - Fast registers (0xF1-0xF7): Every iteration
   - Slow registers (configuration): Every 4th iteration
   - Use non-blocking reads (send multiple R commands, then collect responses)

3. **Interrupt Thread**: Processes position compare data from interrupt queue
   - Parses `P` messages
   - Updates NDArray or equivalent data structures
   - Handles `PR` (reset) and `PX` (complete) events

### Register Synchronization
- After writing a configuration register, read it back to get the actual value
- Some registers are command-type and don't return a value
- Handle 32-bit registers by writing/reading LO then HI components

### System Bus Mapping
- Maintain bidirectional lookup: index ↔ name
- When reading `regMux` registers, translate index to name for display
- When writing `regMux` registers, translate name to index

### Position Compare Data Processing
- Parse `PC_BIT_CAP` to determine which fields are present in `P` messages
- Handle timestamp rollover by detecting backwards time jumps
- Apply scaling and offset transformations to encoder values
- Encoder values are **signed** 32-bit integers (use two's complement)
- System bus and divider values are **unsigned** 32-bit integers

### Configuration Files
- Support reading/writing INI-format configuration files
- Use 4-phase process for robust configuration upload:
  1. Send all W commands
  2. Collect all W responses
  3. Send all R commands (verification)
  4. Collect all R responses and verify values match

---

## Protocol Limitations

1. **No Command Pipelining**: Each write command must wait for its `OK` response before sending the next (except during batch operations)
2. **Fixed Baud Rate**: 115200 is hardcoded in firmware
3. **No Flow Control**: Host must manage message queues to prevent overflow
4. **No Checksums**: Protocol has no built-in error detection beyond command format validation
5. **Limited Error Information**: Error codes don't provide detailed failure reasons
6. **Interrupt Priority**: Interrupt messages (`P`) are interleaved with command responses on the same serial stream

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Auto-generated | Initial specification from zebra driver source code |

---

## References

- Source: [`zebra.cpp`](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/src/zebra.cpp)
- Source: [`zebraRegs.h`](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/src/zebraRegs.h)
- Source: [`zebraTool.py`](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/src/zebraTool.py)
- Source: [`zebra_sim.py`](https://github.com/DiamondLightSource/zebra/blob/84b69dbcc0e085586f799246813e439bea337477/zebraApp/src/zebra_sim.py)
