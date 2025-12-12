"""Top level API.

This package provides asyncio-based serial communication with Diamond Light
Source Zebra position compare and logic hardware.

Phase 1 implementation includes:
- ZebraTransport: Low-level serial I/O
- ZebraProtocol: Register read/write and command execution
- InterruptHandler: Position compare data parsing

Phase 2 implementation includes:
- Complete register definitions (256 registers)
- System bus signal mapping (64 signals)
- Register type classification (RW, RO, CMD, MUX)
- Bidirectional lookup (name ↔ address)
- 32-bit register pair handling

Phase 3 implementation includes:
- Full controller hierarchy with sub-controllers
- AND gates (AND1-4), OR gates (OR1-4)
- Gate generators (GATE1-4)
- Pulse generators (PULSE1-4)
- Pulse dividers (DIV1-4)
- Output routing (OUT1-8)
- Position compare subsystem

Example usage::

    from fastcs_zebra import ZebraTransport, ZebraProtocol

    async with ZebraTransport("/dev/ttyUSB0") as transport:
        protocol = ZebraProtocol(transport)
        value = await protocol.read_register(0xF0)  # Read firmware version
        print(f"Firmware version: {value:#06x}")

    # Using register definitions
    from fastcs_zebra.registers import get_register, RegAddr, SysBus

    reg = get_register("PC_ENC")  # Get by name
    reg = get_register(0x88)       # Get by address
    print(f"PC_ENC is at address {reg.address:#04x}")

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from ._version import __version__
from .controllers import (
    AndGateController,
    DividerController,
    GateController,
    OrGateController,
    OutputController,
    PositionCompareController,
    PulseController,
)
from .interrupts import InterruptHandler, PositionCompareData
from .protocol import (
    MalformedResponseError,
    ProtocolError,
    RegisterError,
    ZebraProtocol,
)
from .register_io import ZebraRegisterIO, ZebraRegisterIORef
from .registers import (
    RegAddr,
    Register,
    Register32,
    RegisterType,
    SysBus,
    get_all_registers,
    get_all_registers_32bit,
    get_register,
    get_register_32bit,
    is_command_register,
    is_mux_register,
    is_readonly_register,
    signal_index_to_name,
    signal_name_to_index,
)
from .transport import ZebraTransport
from .zebra_controller import ZebraController

__all__ = [
    "__version__",
    # Transport and Protocol
    "ZebraTransport",
    "ZebraProtocol",
    "ProtocolError",
    "MalformedResponseError",
    "RegisterError",
    # Interrupts
    "InterruptHandler",
    "PositionCompareData",
    # Controller
    "ZebraController",
    # Sub-controllers
    "AndGateController",
    "OrGateController",
    "GateController",
    "PulseController",
    "DividerController",
    "OutputController",
    "PositionCompareController",
    # Register IO
    "ZebraRegisterIO",
    "ZebraRegisterIORef",
    # Register definitions
    "Register",
    "Register32",
    "RegisterType",
    "RegAddr",
    "SysBus",
    "get_register",
    "get_register_32bit",
    "get_all_registers",
    "get_all_registers_32bit",
    "is_mux_register",
    "is_readonly_register",
    "is_command_register",
    "signal_index_to_name",
    "signal_name_to_index",
]
