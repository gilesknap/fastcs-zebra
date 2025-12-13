"""FastCS controller for Zebra hardware.

Provides EPICS PVs for controlling and monitoring the Zebra position compare
and logic hardware through the serial protocol layer.

Phase 3 implements the full controller hierarchy:
- AND gates (AND1-4)
- OR gates (OR1-4)
- Gate generators (GATE1-4)
- Pulse generators (PULSE1-4)
- Pulse dividers (DIV1-4)
- Output routing (OUT1-8)
- Position compare subsystem
"""

import asyncio
import logging

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command

from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller

from .constants import FAST_UPDATE, SLOW_UPDATE
from .controllers.dividers import DividerController
from .controllers.gates import GateController
from .controllers.logic import AndGateController, OrGateController
from .controllers.outputs import OutputController
from .controllers.position_compare import PositionCompareController
from .controllers.pulses import PulseController
from .interrupts import InterruptHandler, PositionCompareData
from .protocol import ZebraProtocol
from .register_io import ZebraRegisterIO, ZebraRegisterIORef
from .transport import ZebraTransport

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["ZebraController", "ZebraRegisterIO", "ZebraRegisterIORef"]


class ZebraController(Controller):
    """Top-level controller for Zebra hardware.

    Provides a complete controller hierarchy for the Zebra hardware:
    - System status and configuration (top level)
    - Logic gates: AND1-4, OR1-4
    - Gate generators: GATE1-4
    - Pulse generators: PULSE1-4
    - Pulse dividers: DIV1-4
    - Output routing: OUT1-8
    - Position compare subsystem: PC

    Attributes:
        connected: Connection status
        sys_ver: Firmware version
        sys_staterr: System state/error flags
        sys_stat1/2: System bus status (32-bit each)
        soft_in: Software inputs (4 bits)
        div_first: Divider first pulse behavior
        polarity: Output polarity control
        status_msg: Human-readable status message

    Sub-controllers:
        and1-4: AND gate controllers
        or1-4: OR gate controllers
        gate1-4: Gate generator controllers
        pulse1-4: Pulse generator controllers
        div1-4: Pulse divider controllers
        out1-8: Output routing controllers
        pc: Position compare controller
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
        self._sys_stat_update_task: asyncio.Task | None = None

        # Create IO handler (will be set to actual protocol after connect)
        self._register_io = ZebraRegisterIO(None)

        super().__init__(ios=[self._register_io])

        # =====================================================================
        # System Status and Configuration (Top Level)
        # =====================================================================

        # Connection status (no IO, updated manually)
        self.connected = AttrR(Bool())

        # Firmware version (register 0xF0)
        self.sys_ver = AttrR(
            Int(), io_ref=ZebraRegisterIORef(register=0xF0, update_period=SLOW_UPDATE)
        )

        # System state/error (register 0xF1)
        self.sys_staterr = AttrR(
            Int(),
            io_ref=ZebraRegisterIORef(register=0xF1, update_period=SLOW_UPDATE),
        )

        # System bus status (32-bit registers)
        self.sys_stat1 = AttrR(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=0xF2,
                is_32bit=True,
                register_hi=0xF3,
                update_period=FAST_UPDATE,
            ),
        )
        self.sys_stat2 = AttrR(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=0xF4,
                is_32bit=True,
                register_hi=0xF5,
                update_period=FAST_UPDATE,
            ),
        )

        # Number of position compare captures (registers 0xF6/0xF7)
        # Kept for backward compatibility
        self.pc_num_cap = AttrR(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=0xF6,
                is_32bit=True,
                register_hi=0xF7,
                update_period=SLOW_UPDATE,
            ),
        )

        # Position compare encoder selection (register 0x88)
        # Kept for backward compatibility
        self.pc_enc = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=0x88, update_period=SLOW_UPDATE),
        )

        # Position compare timestamp prescaler (register 0x89)
        # Kept for backward compatibility
        self.pc_tspre = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=0x89, update_period=SLOW_UPDATE),
        )

        # Soft inputs (register 0x7F)
        self.soft_in = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=0x7F, update_period=SLOW_UPDATE),
        )

        # Divider first pulse behavior (register 0x7C)
        self.div_first = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=0x7C, update_period=SLOW_UPDATE),
        )

        # Output polarity control (register 0x54)
        self.polarity = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=0x54, update_period=SLOW_UPDATE),
        )

        # Last captured position compare data (updated via interrupts, no IO)
        # Kept for backward compatibility
        self.pc_time_last = AttrR(Int())
        self.pc_enc1_last = AttrR(Int())
        self.pc_enc2_last = AttrR(Int())
        self.pc_enc3_last = AttrR(Int())
        self.pc_enc4_last = AttrR(Int())

        # Status message (no IO)
        self.status_msg = AttrR(String())

        # =====================================================================
        # Sub-controllers
        # =====================================================================

        # Logic gates (AND1-4)
        self.and1 = AndGateController(1, self._register_io)
        self.and2 = AndGateController(2, self._register_io)
        self.and3 = AndGateController(3, self._register_io)
        self.and4 = AndGateController(4, self._register_io)

        # Logic gates (OR1-4)
        self.or1 = OrGateController(1, self._register_io)
        self.or2 = OrGateController(2, self._register_io)
        self.or3 = OrGateController(3, self._register_io)
        self.or4 = OrGateController(4, self._register_io)

        # Gate generators (GATE1-4)
        self.gate1 = GateController(1, self._register_io)
        self.gate2 = GateController(2, self._register_io)
        self.gate3 = GateController(3, self._register_io)
        self.gate4 = GateController(4, self._register_io)

        # Pulse generators (PULSE1-4)
        self.pulse1 = PulseController(1, self._register_io)
        self.pulse2 = PulseController(2, self._register_io)
        self.pulse3 = PulseController(3, self._register_io)
        self.pulse4 = PulseController(4, self._register_io)

        # Pulse dividers (DIV1-4)
        self.div1 = DividerController(1, self._register_io)
        self.div2 = DividerController(2, self._register_io)
        self.div3 = DividerController(3, self._register_io)
        self.div4 = DividerController(4, self._register_io)

        # Output routing (OUT1-8)
        self.out1 = OutputController(1, self._register_io)
        self.out2 = OutputController(2, self._register_io)
        self.out3 = OutputController(3, self._register_io)
        self.out4 = OutputController(4, self._register_io)
        self.out5 = OutputController(5, self._register_io)
        self.out6 = OutputController(6, self._register_io)
        self.out7 = OutputController(7, self._register_io)
        self.out8 = OutputController(8, self._register_io)

        # Position compare subsystem
        self.pc = PositionCompareController(self._register_io)

    async def connect(self) -> None:
        """Connect to Zebra hardware via serial port."""
        try:
            self._transport = ZebraTransport(self._port)
            await self._transport.connect()
            self._protocol = ZebraProtocol(self._transport)

            # Update the IO handler with the actual protocol
            self._register_io.set_protocol(self._protocol)

            # Update connection status
            await self.connected.update(True)
            await self.status_msg.update("Connected")

            # Setup interrupt handler callbacks (only once)
            if not self._callbacks_registered:
                self._setup_interrupt_callbacks()
                self._callbacks_registered = True

            # Start interrupt monitoring
            self._interrupt_task = asyncio.create_task(self._monitor_interrupts())

            # Start system bus status update task
            self._sys_stat_update_task = asyncio.create_task(
                self._update_derived_values()
            )

            logger.info(f"Connected to Zebra on {self._port}")
            await self.status_msg.update(f"Connected to {self._port}")

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            await self.status_msg.update(f"Connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Zebra hardware."""
        # Cancel background tasks
        if self._sys_stat_update_task:
            self._sys_stat_update_task.cancel()
            try:
                await self._sys_stat_update_task
            except asyncio.CancelledError:
                pass
            self._sys_stat_update_task = None

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
            # Update last captured values (top-level for backward compatibility)
            await self.pc_time_last.update(data.timestamp)
            if data.encoder1 is not None:
                await self.pc_enc1_last.update(data.encoder1)
            if data.encoder2 is not None:
                await self.pc_enc2_last.update(data.encoder2)
            if data.encoder3 is not None:
                await self.pc_enc3_last.update(data.encoder3)
            if data.encoder4 is not None:
                await self.pc_enc4_last.update(data.encoder4)

            # Also update position compare controller
            await self.pc.time_last.update(data.timestamp)
            if data.encoder1 is not None:
                await self.pc.enc1_last.update(data.encoder1)
            if data.encoder2 is not None:
                await self.pc.enc2_last.update(data.encoder2)
            if data.encoder3 is not None:
                await self.pc.enc3_last.update(data.encoder3)
            if data.encoder4 is not None:
                await self.pc.enc4_last.update(data.encoder4)

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

    async def _update_derived_values(self) -> None:
        """Background task to update derived values from system bus status.

        This task periodically reads the system bus status and updates
        derived values in all sub-controllers (string representations,
        output states, etc.).
        """
        try:
            while self._transport and self._transport.connected:
                try:
                    # Get current system bus status
                    sys_stat1 = self.sys_stat1.get() or 0
                    sys_stat2 = self.sys_stat2.get() or 0

                    # TODO do this from the sys_stat1/2 AttrR update callbacks
                    # Update all sub-controllers status bits
                    for sub_controller in ZebraSubcontroller.all_controllers:
                        await sub_controller.update_derived_values(sys_stat1, sys_stat2)

                    # Update at 5 Hz (every 0.2 seconds)
                    await asyncio.sleep(FAST_UPDATE)

                except Exception as e:
                    logger.error(f"Error updating derived values: {e}")
                    await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.debug("Derived values update task cancelled")
            raise
