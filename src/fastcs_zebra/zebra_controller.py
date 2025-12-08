"""FastCS controller for Zebra hardware.

Provides EPICS PVs for controlling and monitoring the Zebra position compare
and logic hardware through the serial protocol layer.
"""

import asyncio
import logging

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command

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
        self.connected = AttrR(Bool(), handler=self._get_connected)

        # Firmware version (register 0xF0)
        self.sys_ver = AttrR(Int(), handler=self._get_sys_ver)

        # System state/error (register 0xF1)
        self.sys_staterr = AttrR(Int(), handler=self._get_sys_staterr)

        # Number of position compare captures (registers 0xF6/0xF7)
        self.pc_num_cap = AttrR(Int(), handler=self._get_pc_num_cap)

        # Position compare encoder selection (register 0x88)
        self.pc_enc = AttrRW(
            Int(),
            handler_get=self._get_pc_enc,
            handler_put=self._put_pc_enc,
        )

        # Position compare timestamp prescaler (register 0x89)
        self.pc_tspre = AttrRW(
            Int(),
            handler_get=self._get_pc_tspre,
            handler_put=self._put_pc_tspre,
        )

        # Soft inputs (register 0x7F)
        self.soft_in = AttrRW(
            Int(),
            handler_get=self._get_soft_in,
            handler_put=self._put_soft_in,
        )

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

    # Attribute handlers

    async def _get_connected(self) -> bool:
        """Get connection status."""
        return self._transport is not None and self._transport.connected

    async def _get_sys_ver(self) -> int:
        """Read firmware version register (0xF0)."""
        if not self._protocol:
            return 0
        return await self._protocol.read_register(0xF0)

    async def _get_sys_staterr(self) -> int:
        """Read system state/error register (0xF1)."""
        if not self._protocol:
            return 0
        return await self._protocol.read_register(0xF1)

    async def _get_pc_num_cap(self) -> int:
        """Read number of position compare captures (0xF6/0xF7)."""
        if not self._protocol:
            return 0
        return await self._protocol.read_register_32bit(0xF6, 0xF7)

    async def _get_pc_enc(self) -> int:
        """Read position compare encoder selection (0x88)."""
        if not self._protocol:
            return 0
        return await self._protocol.read_register(0x88)

    async def _put_pc_enc(self, value: int) -> None:
        """Write position compare encoder selection (0x88)."""
        if self._protocol:
            await self._protocol.write_register(0x88, value)

    async def _get_pc_tspre(self) -> int:
        """Read position compare timestamp prescaler (0x89)."""
        if not self._protocol:
            return 0
        return await self._protocol.read_register(0x89)

    async def _put_pc_tspre(self, value: int) -> None:
        """Write position compare timestamp prescaler (0x89)."""
        if self._protocol:
            await self._protocol.write_register(0x89, value)

    async def _get_soft_in(self) -> int:
        """Read soft inputs register (0x7F)."""
        if not self._protocol:
            return 0
        return await self._protocol.read_register(0x7F)

    async def _put_soft_in(self, value: int) -> None:
        """Write soft inputs register (0x7F)."""
        if self._protocol:
            await self._protocol.write_register(0x7F, value & 0x0F)

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
