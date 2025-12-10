# FastCS Zebra EPICS Integration

This document describes how to use the EPICS interface to control and monitor the Zebra hardware.

## Starting the EPICS IOC

Run the FastCS server with:

```bash
python -m fastcs_zebra --port /dev/ttyUSB0 --pv-prefix BL99I-EA-ZEBRA-01:
```

Options:
- `--port`: Serial port path (required)
- `--pv-prefix`: EPICS PV prefix (default: `ZEBRA:`)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--gui`: Generate Phoebus screen file (e.g., `zebra.bob`)

### Generating Phoebus Screens

To automatically generate a Phoebus operator interface screen:

```bash
python -m fastcs_zebra --port /dev/ttyUSB0 \
    --pv-prefix BL99I-EA-ZEBRA-01: \
    --gui zebra.bob
```

This creates a `zebra.bob` file that you can open in Phoebus. The screen automatically includes:
- Connection status indicators
- System information displays
- Position compare controls
- Command buttons
- Real-time readback values

See [Generate Phoebus Screens](../how-to/generate-phoebus-screens.md) for more details.

## Available EPICS PVs

### Connection Status

- `$(PREFIX)CONNECTED`: Boolean - Connection status to Zebra hardware

### Firmware and Status

- `$(PREFIX)SYS_VER`: Integer - Firmware version (register 0xF0)
- `$(PREFIX)SYS_STATERR`: Integer - System state/error flags (register 0xF1)
- `$(PREFIX)STATUS_MSG`: String - Human-readable status message

### Position Compare Control

- `$(PREFIX)PC_ENC`: Integer RW - Encoder selection (register 0x88)
  - 0: Encoder 1
  - 1: Encoder 2
  - 2: Encoder 3
  - 3: Encoder 4
  - 4: Encoder 1+2+3+4 (sum)

- `$(PREFIX)PC_TSPRE`: Integer RW - Timestamp prescaler (register 0x89)
  - 5: Millisecond units
  - 5000: Second units
  - 500000: 10-second units

- `$(PREFIX)PC_NUM_CAP`: Integer - Number of position compare captures (registers 0xF6/0xF7)

### Position Compare Commands

- `$(PREFIX)PC_ARM`: Command - Arm position compare (write 0x8B)
- `$(PREFIX)PC_DISARM`: Command - Disarm position compare (write 0x8C)

### Last Captured Data (Updated via Interrupts)

- `$(PREFIX)PC_TIME_LAST`: Integer - Last captured timestamp
- `$(PREFIX)PC_ENC1_LAST`: Integer - Last captured encoder 1 value
- `$(PREFIX)PC_ENC2_LAST`: Integer - Last captured encoder 2 value
- `$(PREFIX)PC_ENC3_LAST`: Integer - Last captured encoder 3 value
- `$(PREFIX)PC_ENC4_LAST`: Integer - Last captured encoder 4 value

### Soft Inputs

- `$(PREFIX)SOFT_IN`: Integer RW - Software input bits (register 0x7F)
  - Bits 0-3 correspond to SOFT_IN1-4 on system bus

### Flash Storage Commands

- `$(PREFIX)SAVE_TO_FLASH`: Command - Save configuration to flash memory
- `$(PREFIX)LOAD_FROM_FLASH`: Command - Load configuration from flash memory

### System Control

- `$(PREFIX)SYS_RESET`: Command - Reset Zebra system (write 0x7E)

## Testing with EPICS Tools

### Reading Values

```bash
# Check connection status
caget BL99I-EA-ZEBRA-01:CONNECTED

# Read firmware version
caget BL99I-EA-ZEBRA-01:SYS_VER

# Check status message
caget BL99I-EA-ZEBRA-01:STATUS_MSG

# Monitor position compare captures
camonitor BL99I-EA-ZEBRA-01:PC_NUM_CAP
```

### Writing Values

```bash
# Set soft inputs
caput BL99I-EA-ZEBRA-01:SOFT_IN 5  # Set bits 0 and 2

# Select encoder 1 for position compare
caput BL99I-EA-ZEBRA-01:PC_ENC 0

# Set timestamp prescaler to seconds
caput BL99I-EA-ZEBRA-01:PC_TSPRE 5000
```

### Executing Commands

```bash
# Arm position compare
caput BL99I-EA-ZEBRA-01:PC_ARM 1

# Monitor last captured values
camonitor BL99I-EA-ZEBRA-01:PC_TIME_LAST
camonitor BL99I-EA-ZEBRA-01:PC_ENC1_LAST

# Disarm position compare
caput BL99I-EA-ZEBRA-01:PC_DISARM 1

# Save configuration to flash
caput BL99I-EA-ZEBRA-01:SAVE_TO_FLASH 1
```

## Example Session

```bash
# Start the IOC
python -m fastcs_zebra --port /dev/ttyUSB0 --pv-prefix TEST:ZEBRA:

# In another terminal, test the connection
caget TEST:ZEBRA:CONNECTED
# Should return: TEST:ZEBRA:CONNECTED 1

# Read firmware version
caget TEST:ZEBRA:SYS_VER
# Example: TEST:ZEBRA:SYS_VER 32  (0x20)

# Set soft input bits
caput TEST:ZEBRA:SOFT_IN 3
# Sets SOFT_IN1 and SOFT_IN2 high

# Configure position compare
caput TEST:ZEBRA:PC_ENC 0        # Use encoder 1
caput TEST:ZEBRA:PC_TSPRE 5      # Millisecond timestamps

# Monitor captures in real-time
camonitor TEST:ZEBRA:PC_NUM_CAP TEST:ZEBRA:PC_ENC1_LAST &

# Arm position compare (starts capturing)
caput TEST:ZEBRA:PC_ARM 1

# Wait for data...

# Disarm when done
caput TEST:ZEBRA:PC_DISARM 1
```

## Architecture Notes

The EPICS integration uses:
- **FastCS**: Modern Python framework for EPICS device support
- **Channel Access Transport**: Standard EPICS protocol (CA)
- **Asyncio**: Non-blocking serial I/O with interrupt monitoring
- **Background Task**: Monitors for position compare interrupts and updates PVs

When position compare is armed, the controller:
1. Monitors serial port for interrupt messages (PR, P<data>, PX)
2. Parses position compare data from P messages
3. Updates `PC_*_LAST` PVs with latest captured values
4. Updates `STATUS_MSG` on reset/complete events

All register I/O happens asynchronously without blocking EPICS operations.
