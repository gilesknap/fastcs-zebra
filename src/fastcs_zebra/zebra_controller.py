"""FastCS controller for Zebra hardware.

Provides EPICS PVs for controlling and monitoring the Zebra position compare
and logic hardware through the serial protocol layer.
"""

import asyncio
import logging

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command, scan

from .interrupts import InterruptHandler, PositionCompareData
from .protocol import ZebraProtocol
from .transport import ZebraTransport

logger = logging.getLogger(__name__)


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
        super().__init__()

        self._port = port
        self._transport: ZebraTransport | None = None
        self._protocol: ZebraProtocol | None = None
        self._interrupt_handler = InterruptHandler()
        self._interrupt_task: asyncio.Task | None = None

        # Connection status
        self.connected = AttrR(Bool())

        # Firmware version (register 0xF0)
        self.sys_ver = AttrR(Int())

        # System state/error (register 0xF1)
        self.sys_staterr = AttrR(Int())

        # Number of position compare captures (registers 0xF6/0xF7)
        self.pc_num_cap = AttrR(Int())

        # Position compare encoder selection (register 0x88)
        self.pc_enc = AttrRW(Int())
        self.pc_enc.set_on_put_callback(self._on_put_pc_enc)

        # Position compare timestamp prescaler (register 0x89)
        self.pc_tspre = AttrRW(Int())
        self.pc_tspre.set_on_put_callback(self._on_put_pc_tspre)

        # Soft inputs (register 0x7F)
        self.soft_in = AttrRW(Int())
        self.soft_in.set_on_put_callback(self._on_put_soft_in)

        # Last captured position compare data (updated via interrupts)
        self.pc_time_last = AttrR(Int())
        self.pc_enc1_last = AttrR(Int())
        self.pc_enc2_last = AttrR(Int())
        self.pc_enc3_last = AttrR(Int())
        self.pc_enc4_last = AttrR(Int())

        # Status message
        self.status_msg = AttrR(String())

    async def connect(self) -> None:
        """Connect to Zebra hardware via serial port."""
        try:
            self._transport = ZebraTransport(self._port)
            await self._transport.connect()
            self._protocol = ZebraProtocol(self._transport)

            # Setup interrupt handler callbacks
            @self._interrupt_handler.on_reset
            async def on_reset():
                logger.info("Position compare reset")
                await self.status_msg.set("PC Reset")

            @self._interrupt_handler.on_data
            async def on_data(data: PositionCompareData):
                # Update last captured values
                await self.pc_time_last.set(data.timestamp)
                if data.encoder1 is not None:
                    await self.pc_enc1_last.set(data.encoder1)
                if data.encoder2 is not None:
                    await self.pc_enc2_last.set(data.encoder2)
                if data.encoder3 is not None:
                    await self.pc_enc3_last.set(data.encoder3)
                if data.encoder4 is not None:
                    await self.pc_enc4_last.set(data.encoder4)

            @self._interrupt_handler.on_end
            async def on_end():
                logger.info("Position compare complete")
                await self.status_msg.set("PC Complete")

            # Start interrupt monitoring
            self._interrupt_task = asyncio.create_task(self._monitor_interrupts())

            logger.info(f"Connected to Zebra on {self._port}")
            await self.status_msg.set(f"Connected to {self._port}")

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            await self.status_msg.set(f"Connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Zebra hardware."""
        if self._interrupt_task:
            self._interrupt_task.cancel()
            try:
                await self._interrupt_task
            except asyncio.CancelledError:
                pass

        if self._transport:
            await self._transport.disconnect()
            self._transport = None
            self._protocol = None

        logger.info("Disconnected from Zebra")
        await self.status_msg.set("Disconnected")

    async def _monitor_interrupts(self) -> None:
        """Background task to monitor for interrupt messages."""
        while self._transport and self._transport.connected:
            try:
                # Try to read with short timeout
                message = await self._transport.read_line(timeout=0.1)

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

    # Periodic scans to update read-only attributes

    @scan(1.0)  # Update every second
    async def update_status(self):
        """Periodically update connection, version, and status attributes."""
        if self._transport and self._transport.connected:
            await self.connected.update(True)

            if self._protocol:
                # Read firmware version
                try:
                    version = await self._protocol.read_register(0xF0)
                    await self.sys_ver.update(version)
                except Exception as e:
                    logger.error(f"Error reading sys_ver: {e}")

                # Read system state/error
                try:
                    staterr = await self._protocol.read_register(0xF1)
                    await self.sys_staterr.update(staterr)
                except Exception as e:
                    logger.error(f"Error reading sys_staterr: {e}")

                # Read position compare capture count
                try:
                    num_cap = await self._protocol.read_register_32bit(0xF6, 0xF7)
                    await self.pc_num_cap.update(num_cap)
                except Exception as e:
                    logger.error(f"Error reading pc_num_cap: {e}")

                # Read current register values for RW attributes
                try:
                    pc_enc = await self._protocol.read_register(0x88)
                    await self.pc_enc.update(pc_enc)
                except Exception as e:
                    logger.error(f"Error reading pc_enc: {e}")

                try:
                    pc_tspre = await self._protocol.read_register(0x89)
                    await self.pc_tspre.update(pc_tspre)
                except Exception as e:
                    logger.error(f"Error reading pc_tspre: {e}")

                try:
                    soft_in = await self._protocol.read_register(0x7F)
                    await self.soft_in.update(soft_in)
                except Exception as e:
                    logger.error(f"Error reading soft_in: {e}")
        else:
            await self.connected.update(False)

    # AttrRW on_put callbacks

    async def _on_put_pc_enc(self, attr: AttrRW, value: int) -> None:
        """Write position compare encoder selection (0x88)."""
        if self._protocol:
            await self._protocol.write_register(0x88, value)
            # Update the readback value
            actual = await self._protocol.read_register(0x88)
            await attr.update(actual)

    async def _on_put_pc_tspre(self, attr: AttrRW, value: int) -> None:
        """Write position compare timestamp prescaler (0x89)."""
        if self._protocol:
            await self._protocol.write_register(0x89, value)
            # Update the readback value
            actual = await self._protocol.read_register(0x89)
            await attr.update(actual)

    async def _on_put_soft_in(self, attr: AttrRW, value: int) -> None:
        """Write soft inputs register (0x7F)."""
        if self._protocol:
            await self._protocol.write_register(0x7F, value & 0x0F)
            # Update the readback value
            actual = await self._protocol.read_register(0x7F)
            await attr.update(actual)

    # Commands

    @command()
    async def pc_arm(self) -> None:
        """Arm position compare (write 0x8B)."""
        if self._protocol:
            await self._protocol.write_register(0x8B, 1)
            logger.info("Position compare armed")
            await self.status_msg.set("PC Armed")

    @command()
    async def pc_disarm(self) -> None:
        """Disarm position compare (write 0x8C)."""
        if self._protocol:
            await self._protocol.write_register(0x8C, 1)
            logger.info("Position compare disarmed")
            await self.status_msg.set("PC Disarmed")

    @command()
    async def save_to_flash(self) -> None:
        """Save configuration to flash memory."""
        if self._protocol:
            await self._protocol.flash_command("S")
            logger.info("Configuration saved to flash")
            await self.status_msg.set("Saved to flash")

    @command()
    async def load_from_flash(self) -> None:
        """Load configuration from flash memory."""
        if self._protocol:
            await self._protocol.flash_command("L")
            logger.info("Configuration loaded from flash")
            await self.status_msg.set("Loaded from flash")

    @command()
    async def sys_reset(self) -> None:
        """Reset Zebra system (write 0x7E)."""
        if self._protocol:
            await self._protocol.write_register(0x7E, 1)
            logger.info("System reset")
            await self.status_msg.set("System reset")
