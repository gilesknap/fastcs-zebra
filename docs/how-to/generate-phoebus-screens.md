# Generate Phoebus Screens

FastCS automatically generates Phoebus (CS-Studio) operator interface screens (`.bob` files) for your Zebra controller.

## Quick Start

To generate a Phoebus screen when starting the IOC:

```bash
uv run python -m fastcs_zebra \
    --port /dev/ttyUSB0 \
    --pv-prefix BL99I-EA-ZEBRA-01: \
    --gui zebra.bob
```

This will create a `zebra.bob` file in the current directory that you can open in Phoebus.

## With the Simulator

For testing with the simulator:

```bash
uv run python -m fastcs_zebra \
    --port sim://zebra01 \
    --pv-prefix TEST-ZEB \
    --gui zebra.bob
```

## Screen Generation

The screen is generated **automatically** when the IOC starts based on your controller's attributes and sub-controllers. The screen will include:

- **Read-only fields** (from `AttrR`) displayed as text indicators
- **Read-write fields** (from `AttrRW`) displayed as editable text fields with readback
- **Write-only fields** (from `AttrW`) displayed as controls
- **Commands** (from `@command` decorator) displayed as buttons
- **Sub-controllers** displayed as buttons that open sub-screens

## Screen Layout

The generated Phoebus screen for the Zebra will organize widgets based on the controller structure:

```
Zebra Position Compare Controller
├── Connection Status (LED indicator)
├── System Info
│   ├── Firmware Version
│   └── System State/Error
├── Position Compare Controls
│   ├── Encoder Selection
│   ├── Prescaler
│   ├── Arm/Disarm commands
│   └── Last Captured Values
└── Commands
    ├── Save to Flash
    ├── Load from Flash
    └── System Reset
```

## Advanced Options

### Programmatic Screen Generation

If you need more control over screen generation, you can create screens programmatically:

```python
from pathlib import Path
from fastcs.launch import FastCS
from fastcs.transports.epics.ca import EpicsCATransport
from fastcs.transports.epics.options import EpicsGUIOptions, EpicsIOCOptions
from fastcs_zebra.zebra_controller import ZebraController

# Setup GUI options
gui_options = EpicsGUIOptions(
    output_path=Path("./opi/zebra.bob"),
    title="Diamond Zebra Controller",
)

# Create controller and transport
controller = ZebraController(port="/dev/ttyUSB0")
transport = EpicsCATransport(
    gui=gui_options,
    epicsca=EpicsIOCOptions(pv_prefix="BL99I-EA-ZEBRA-01:"),
)

# Launch IOC
fastcs = FastCS(controller, [transport])
fastcs.run()
```

## Opening Screens in Phoebus

Once the `.bob` file is generated:

1. Open Phoebus
2. Navigate to **File → Open** or press `Ctrl+O`
3. Select your generated `zebra.bob` file
4. The screen will display with live connections to your running IOC

Alternatively, you can launch Phoebus from the command line:

```bash
phoebus.sh -resource zebra.bob
```

## Customization

The screen layout is automatically determined by your controller structure. To customize:

1. **Group related attributes**: Use the `group` parameter in attribute definitions
2. **Add descriptions**: Set `desc` parameter for tooltips and labels
3. **Control visibility**: Attributes marked as `INTERNAL` won't appear on screens
4. **Organize with sub-controllers**: Related functionality in sub-controllers generates sub-screens

## Screen Updates

The screen file is generated each time the IOC starts. If you modify your controller structure (add/remove attributes, change groups, etc.), simply restart the IOC to regenerate the updated screen.

## Troubleshooting

### Screen not generated

If the screen file isn't created:

1. Check file permissions in the output directory
2. Verify the path is valid (parent directories must exist or will be created)
3. Check the IOC startup logs for errors

### Widgets not displaying correctly

- Ensure your FastCS version is up to date: `uv pip install --upgrade 'fastcs[epics]'`
- Check that attribute types are supported (String, Int, Float, Bool, Enum, Waveform)
- Verify PV prefix matches between IOC and Phoebus

### PVs not connecting

1. Check that the IOC is running
2. Verify `EPICS_CA_ADDR_LIST` is configured correctly
3. Use `caget` to test PV connectivity: `caget <PV_PREFIX>:Connected`
