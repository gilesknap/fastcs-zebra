"""Top level API.

This package provides asyncio-based serial communication with Diamond Light
Source Zebra position compare and logic hardware.

Phase 1 implementation includes:
- ZebraTransport: Low-level serial I/O
- ZebraProtocol: Register read/write and command execution
- InterruptHandler: Position compare data parsing
- CLI: Interactive testing interface

Example usage:
    >>> from fastcs_zebra import ZebraTransport, ZebraProtocol
    >>> async with ZebraTransport("/dev/ttyUSB0") as transport:
    ...     protocol = ZebraProtocol(transport)
    ...     value = await protocol.read_register(0xF0)  # Read firmware version
    ...     print(f"Firmware version: {value:#06x}")

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from ._version import __version__
from .interrupts import InterruptHandler, PositionCompareData
from .protocol import (
    MalformedResponseError,
    ProtocolError,
    RegisterError,
    ZebraProtocol,
)
from .transport import ZebraTransport

__all__ = [
    "__version__",
    "ZebraTransport",
    "ZebraProtocol",
    "ProtocolError",
    "MalformedResponseError",
    "RegisterError",
    "InterruptHandler",
    "PositionCompareData",
]
