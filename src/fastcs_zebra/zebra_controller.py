"""FastCS controller for Zebra hardware.

Provides EPICS PVs for controlling and monitoring the Zebra position compare
and logic hardware through the serial protocol layer.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import TypeVar

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command

from .interrupts import InterruptHandler, PositionCompareData
from .protocol import ZebraProtocol
from .transport import ZebraTransport

logger = logging.getLogger(__name__)

NumberT = TypeVar("NumberT", int, float)


@dataclass
class ZebraRegisterIORef(AttributeIORef):
    """Reference for Zebra register IO operations."""

    register: int = 0  # Register address (0x00-0xFF)
    is_32bit: bool = False  # True if this is a 32-bit register pair
    register_hi: int | None = None  # High register for 32-bit values
    update_period: float | None = 1.0  # Poll every second by default


class ZebraRegisterIO(AttributeIO[NumberT, ZebraRegisterIORef]):
    """Handles reading from and writing to Zebra registers."""

    def __init__(self, protocol: ZebraProtocol | None):
        super().__init__()
        self._protocol = protocol

    def set_protocol(self, protocol: ZebraProtocol) -> None:
        """Set the protocol instance for register I/O operations."""
        self._protocol = protocol

    async def update(self, attr):
        """Read value from Zebra register and update attribute."""
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
            logger.error(f"Error reading register 0x{attr.io_ref.register:02X}: {e}")

    async def send(self, attr, value):
        """Write attribute value to Zebra register."""
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
            logger.error(f"Error writing register 0x{attr.io_ref.register:02X}: {e}")


class ZebraController(Controller):
    """Top-level controller for Zebra hardware.

    Exposes connection management, firmware version, and register access
    for testing Phase 1 serial communication functionality.
    """

    def __init__(self, port: str):
        """Initialize Zebra controller.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0', 'COM3')
        """
        self._port = port
        self._transport: ZebraTransport | None = None
        self._protocol: ZebraProtocol | None = None
        self._interrupt_handler = InterruptHandler()
        self._interrupt_task: asyncio.Task | None = None
        self._callbacks_registered = False

        # Create IO handler (will be set to actual protocol after connect)
        self._register_io = ZebraRegisterIO(None)

        super().__init__(ios=[self._register_io])

        # Connection status (no IO, updated manually)
        self.connected = AttrR(Bool())

        # Firmware version (register 0xF0)
        self.sys_ver = AttrR(
            Int(), io_ref=ZebraRegisterIORef(register=0xF0, update_period=10.0)
        )

        # System state/error (register 0xF1)
        self.sys_staterr = AttrR(
            Int(), io_ref=ZebraRegisterIORef(register=0xF1, update_period=1.0)
        )

        # Number of position compare captures (registers 0xF6/0xF7)
        self.pc_num_cap = AttrR(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=0xF6, is_32bit=True, register_hi=0xF7, update_period=1.0
            ),
        )

        # Position compare encoder selection (register 0x88)
        self.pc_enc = AttrRW(
            Int(), io_ref=ZebraRegisterIORef(register=0x88, update_period=1.0)
        )

        # Position compare timestamp prescaler (register 0x89)
        self.pc_tspre = AttrRW(
            Int(), io_ref=ZebraRegisterIORef(register=0x89, update_period=1.0)
        )

        # Soft inputs (register 0x7F)
        self.soft_in = AttrRW(
            Int(), io_ref=ZebraRegisterIORef(register=0x7F, update_period=1.0)
        )

        # Last captured position compare data (updated via interrupts, no IO)
        self.pc_time_last = AttrR(Int())
        self.pc_enc1_last = AttrR(Int())
        self.pc_enc2_last = AttrR(Int())
        self.pc_enc3_last = AttrR(Int())
        self.pc_enc4_last = AttrR(Int())

        # Status message (no IO)
        self.status_msg = AttrR(String())

    async def connect(self) -> None:
        """Connect to Zebra hardware via serial port."""
        try:
            self._transport = ZebraTransport(self._port)
            await self._transport.connect()
            self._protocol = ZebraProtocol(self._transport)

            # Update the IO handler with the actual protocol
            self._register_io.set_protocol(self._protocol)

            # Connect attribute IOs (sets up put callbacks)
            self._connect_attribute_ios()

            # Update connection status
            await self.connected.update(True)
            await self.status_msg.update("Connected")

            # Setup interrupt handler callbacks (only once)
            if not self._callbacks_registered:
                self._setup_interrupt_callbacks()
                self._callbacks_registered = True

            # Start interrupt monitoring
            self._interrupt_task = asyncio.create_task(self._monitor_interrupts())

            logger.info(f"Connected to Zebra on {self._port}")
            await self.status_msg.update(f"Connected to {self._port}")

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            await self.status_msg.update(f"Connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Zebra hardware."""
        if self._interrupt_task:
            self._interrupt_task.cancel()
            try:
                await self._interrupt_task
            except asyncio.CancelledError:
                pass
            self._interrupt_task = None

        if self._transport:
            await self._transport.disconnect()
            self._transport = None
            self._protocol = None

        await self.connected.update(False)
        logger.info("Disconnected from Zebra")
        await self.status_msg.update("Disconnected")

    def _setup_interrupt_callbacks(self) -> None:
        """Setup interrupt handler callbacks. Called once during first connect."""

        @self._interrupt_handler.on_reset
        async def on_reset():
            logger.info("Position compare reset")
            await self.status_msg.update("PC Reset")

        @self._interrupt_handler.on_data
        async def on_data(data: PositionCompareData):
            # Update last captured values
            await self.pc_time_last.update(data.timestamp)
            if data.encoder1 is not None:
                await self.pc_enc1_last.update(data.encoder1)
            if data.encoder2 is not None:
                await self.pc_enc2_last.update(data.encoder2)
            if data.encoder3 is not None:
                await self.pc_enc3_last.update(data.encoder3)
            if data.encoder4 is not None:
                await self.pc_enc4_last.update(data.encoder4)

        @self._interrupt_handler.on_end
        async def on_end():
            logger.info("Position compare complete")
            await self.status_msg.update("PC Complete")

    async def _monitor_interrupts(self) -> None:
        """Background task to monitor for interrupt messages."""
        try:
            while self._transport and self._transport.connected:
                try:
                    # Try to read interrupt with short timeout
                    message = await self._transport.read_interrupt(timeout=0.1)

                    # Check if it's an interrupt
                    if message.startswith("P"):
                        await self._interrupt_handler.handle_message(message)
                    else:
                        logger.warning(f"Unexpected message: {message!r}")

                except TimeoutError:
                    # No data available, continue
                    await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error monitoring interrupts: {e}")
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Task was cancelled during shutdown - this is expected
            logger.debug("Interrupt monitoring task cancelled")
            raise

    def _check_connected(self) -> None:
        """Check if connected and raise RuntimeError if not."""
        if not self._protocol:
            raise RuntimeError("Not connected to Zebra hardware")

    # Commands

    @command()
    async def pc_arm(self) -> None:
        """Arm position compare (write 0x8B)."""
        self._check_connected()
        await self._protocol.write_register(0x8B, 1)  # type: ignore[union-attr]
        logger.info("Position compare armed")
        await self.status_msg.update("PC Armed")

    @command()
    async def pc_disarm(self) -> None:
        """Disarm position compare (write 0x8C)."""
        self._check_connected()
        await self._protocol.write_register(0x8C, 1)  # type: ignore[union-attr]
        logger.info("Position compare disarmed")
        await self.status_msg.update("PC Disarmed")

    @command()
    async def save_to_flash(self) -> None:
        """Save configuration to flash memory."""
        self._check_connected()
        await self._protocol.flash_command("S")  # type: ignore[union-attr]
        logger.info("Configuration saved to flash")
        await self.status_msg.update("Saved to flash")

    @command()
    async def load_from_flash(self) -> None:
        """Load configuration from flash memory."""
        self._check_connected()
        await self._protocol.flash_command("L")  # type: ignore[union-attr]
        logger.info("Configuration loaded from flash")
        await self.status_msg.update("Loaded from flash")

    @command()
    async def sys_reset(self) -> None:
        """Reset Zebra system (write 0x7E)."""
        self._check_connected()
        await self._protocol.write_register(0x7E, 1)  # type: ignore[union-attr]
        logger.info("System reset")
        await self.status_msg.update("System reset")
