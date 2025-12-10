# Zebra Serial Protocol

This document describes the serial communication protocol used by FastCS-Zebra to communicate with the Zebra hardware device.

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

### Read Register Command

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

### Write Register Command

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

**Note**: Read-only registers will reject write commands.

### Flash Storage Commands

#### Save to Flash

**Format**: `S\n`

**Response**: `SOK\n`

**Purpose**: Saves the current register configuration to non-volatile flash memory.

**Note**: This command may take ~100ms to complete.

#### Load from Flash

**Format**: `L\n`

**Response**: `LOK\n`

**Purpose**: Restores register configuration from non-volatile flash memory.

### Generic Error Response

**Format**: `E0\n`

**Purpose**: Indicates a malformed or unrecognized command.

## Interrupt Messages (Asynchronous)

The Zebra sends unsolicited messages when position compare events occur. These messages are distinguished by starting with the letter `P`.

### Position Compare Reset Message

**Format**: `PR\n`

**Meaning**: Position compare has been armed. The host should reset its data buffers and prepare to receive position compare data.

**Trigger**: Sent when register `PC_ARM` (0x8B) is written with value 1.

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

### Position Compare Complete Message

**Format**: `PX\n`

**Meaning**: Position compare acquisition has completed. No more data will be sent.

**Trigger**: Sent when:
- Register `PC_DISARM` (0x8C) is written with value 1, OR
- The configured number of pulses has been generated and captured

## Key Registers

### Position Compare Control

- `0x88` - `PC_ENC` - Select which encoder to use for position compare
- `0x89` - `PC_TSPRE` - Timestamp clock prescaler (5=milliseconds, 5000=seconds)
- `0x8A` - `PC_ARM_SEL` - Arm input source (0=software, 1=external)
- `0x8B` - `PC_ARM` - Software arm command
- `0x8C` - `PC_DISARM` - Software disarm command
- `0x9F` - `PC_BIT_CAP` - Bit mask for data capture (which encoders/divs/sysbus)

### System Status (Read-Only)

- `0xF0` - `SYS_VER` - Firmware version
- `0xF1` - `SYS_STATERR` - System state/error flags
- `0xF2` - `SYS_STAT1LO` - System bus status bits 0-15
- `0xF3` - `SYS_STAT1HI` - System bus status bits 16-31
- `0xF4` - `SYS_STAT2LO` - System bus status bits 32-47
- `0xF5` - `SYS_STAT2HI` - System bus status bits 48-63
- `0xF6` - `PC_NUM_CAPLO` - Number of position compare captures (low 16 bits)
- `0xF7` - `PC_NUM_CAPHI` - Number of position compare captures (high 16 bits)

### Other Key Registers

- `0x7E` - `SYS_RESET` - System reset command
- `0x7F` - `SOFT_IN` - Software input register (4 bits for SOFT_IN1-4)

**Note**: For a complete register map with all 256 registers, see the [legacy Zebra repository](https://github.com/DiamondLightSource/zebra).

## Implementation in FastCS-Zebra

The FastCS-Zebra driver implements this protocol through the following classes:

- **{class}`~fastcs_zebra.transport.ZebraTransport`** - Handles low-level serial I/O with asyncio
- **{class}`~fastcs_zebra.protocol.ZebraProtocol`** - Implements command/response parsing and validation
- **{class}`~fastcs_zebra.interrupts.InterruptHandler`** - Processes asynchronous position compare data

See the [Architecture](../explanations/architecture.md) documentation for details on how these components interact.

## See Also

- [Complete Serial Protocol Specification](https://github.com/DiamondLightSource/zebra/blob/main/docs/SERIAL_PROTOCOL_SPEC.md) - Full specification with all registers
- [EPICS PV Interface Specification](https://github.com/DiamondLightSource/zebra/blob/main/docs/EPICS_PV_SPEC.md) - How EPICS PVs map to registers
