"""Zebra register I/O classes for FastCS attributes.

This module contains the AttributeIO classes that handle reading and writing
to Zebra registers. They are separated from the main controller to avoid
circular imports with sub-controllers.
"""

from dataclasses import dataclass
from typing import TypeVar

from fastcs.attributes import AttributeIO, AttributeIORef, AttrRW

NumberT = TypeVar("NumberT", int, float)


@dataclass
class ZebraRegisterIORef(AttributeIORef):
    """Reference for Zebra register IO operations.

    Attributes:
        register: Register address (0x00-0xFF)
        is_32bit: True if this is a 32-bit register pair
        register_hi: High register address for 32-bit values
        update_period: Poll period in seconds (default 1.0)
    """

    register: int = 0  # Register address (0x00-0xFF)
    is_32bit: bool = False  # True if this is a 32-bit register pair
    register_hi: int | None = None  # High register for 32-bit values
    update_period: float | None = 1.0  # Poll every second by default


class ZebraRegisterIO(AttributeIO[NumberT, ZebraRegisterIORef]):
    """Handles reading from and writing to Zebra registers.

    This class bridges FastCS attributes with the Zebra serial protocol.
    It uses the ZebraProtocol instance to perform actual I/O operations.
    """

    def __init__(self, protocol=None):
        """Initialize register IO handler.

        Args:
            protocol: ZebraProtocol instance (can be None initially)
        """
        super().__init__()
        self._protocol = protocol
        self._logger = None

    def set_protocol(self, protocol) -> None:
        """Set the protocol instance for register I/O operations.

        Args:
            protocol: ZebraProtocol instance
        """
        self._protocol = protocol

    async def update(self, attr):
        """Read value from Zebra register and update attribute.

        Args:
            attr: The attribute to update
        """
        if not self._protocol:
            return

        try:
            if attr.io_ref.is_32bit and attr.io_ref.register_hi is not None:
                value = await self._protocol.read_register_32bit(
                    attr.io_ref.register, attr.io_ref.register_hi
                )
            else:
                value = await self._protocol.read_register(attr.io_ref.register)

            await attr.update(attr.dtype(value))
        except Exception as e:
            # Import logging here to avoid circular imports at module level
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error reading register 0x{attr.io_ref.register:02X}: {e}")

    async def send(self, attr, value):
        """Write attribute value to Zebra register.

        Args:
            attr: The attribute being written
            value: The value to write
        """
        if not self._protocol:
            return

        try:
            int_value = int(value)
            if attr.io_ref.is_32bit and attr.io_ref.register_hi is not None:
                # Write 32-bit value as LO/HI pair
                lo_value = int_value & 0xFFFF
                hi_value = (int_value >> 16) & 0xFFFF
                await self._protocol.write_register(attr.io_ref.register, lo_value)
                await self._protocol.write_register(attr.io_ref.register_hi, hi_value)
            else:
                await self._protocol.write_register(attr.io_ref.register, int_value)

            # Read back and update the attribute to reflect actual hardware state
            # Only if this is a read-write attribute (AttrRW has update method)
            if isinstance(attr, AttrRW):
                await self.update(attr)

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error writing register 0x{attr.io_ref.register:02X}: {e}")
