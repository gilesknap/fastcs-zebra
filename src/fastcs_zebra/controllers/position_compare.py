"""Position compare sub-controller.

The position compare system captures encoder positions, divider counts,
and system bus state synchronized with motion. It provides:
- Configurable encoder selection
- Gate control (position-based, time-based, or external)
- Pulse control (position-based, time-based, or external)
- Data capture selection (encoders, system bus, dividers)
- Captured data arrays and last values

This controller manages the complete position compare subsystem including
arm/disarm, configuration, and interrupt-driven data updates.
"""

from typing import TYPE_CHECKING

from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import Bool, Enum, Int
from fastcs.methods import command

if TYPE_CHECKING:
    from fastcs_zebra.interrupts import InterruptHandler
from fastcs_zebra.constants import SLOW_UPDATE
from fastcs_zebra.controllers.enums import (
    ArmSelection,
    Direction,
    EncoderSelection,
    Prescaler,
    SourceSelection,
)
from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import (
    REGISTERS_32BIT_BY_NAME,
    SysBus,
)


class PositionCompareController(ZebraSubcontroller):
    """Controller for the position compare subsystem.

    The position compare system captures encoder positions synchronized with
    motion events. It supports:
    - Position-based or time-based gating
    - Position-based or time-based pulse generation
    - Capture of up to 4 encoders, 2 system bus states, and 4 divider counts
    - Configurable direction and timing parameters

    Attributes:
        # Encoder and timing selection
        enc: Encoder selection (0-4)
        enc_str: Human-readable encoder name
        tspre: Timestamp prescaler
        tspre_str: Human-readable prescaler
        dir: Direction (0=positive, 1=negative)
        dir_str: Human-readable direction

        # Arm configuration
        arm_sel: Arm source (0=software, 1=external)
        arm_sel_str: Human-readable arm source
        arm_inp: External arm input (system bus index)
        arm_inp_str: Human-readable arm input name

        # Gate configuration
        gate_sel: Gate source (0=position, 1=time, 2=external)
        gate_sel_str: Human-readable gate source
        gate_inp: External gate input (system bus index)
        gate_inp_str: Human-readable gate input name
        gate_start: Gate start position/time (32-bit)
        gate_wid: Gate width (32-bit)
        gate_ngate: Number of gates (32-bit)
        gate_step: Gate step size (32-bit)
        gate_out: Current gate output state

        # Pulse configuration
        pulse_sel: Pulse source (0=position, 1=time, 2=external)
        pulse_sel_str: Human-readable pulse source
        pulse_inp: External pulse input (system bus index)
        pulse_inp_str: Human-readable pulse input name
        pulse_start: Pulse start position/time (32-bit)
        pulse_wid: Pulse width (32-bit)
        pulse_step: Pulse step size (32-bit)
        pulse_max: Maximum pulses (32-bit)
        pulse_dly: Pulse delay (32-bit)
        pulse_out: Current pulse output state

        # Capture configuration
        bit_cap: Capture bit mask (10 bits)
        num_cap: Number of captures (32-bit, read-only)

        # Status
        arm_out: Current arm output state

        # Last captured values - updated by interrupts
        time_last: Last captured timestamp
        enc1_last - enc4_last: Last captured encoder values
    """

    count = 1  # Only one position compare controller

    def __init__(
        self,
        register_io: ZebraRegisterIO,
    ):
        """Initialize position compare controller.

        Args:
            register_io: Shared register IO handler
        """
        super().__init__(1, register_io)
        self._interrupt_handler: InterruptHandler | None = None

        # =====================================================================
        # Encoder and Timing Selection
        # =====================================================================
        self.enc = self.make_rw_attr("PC_ENC", Enum(EncoderSelection))
        self.tspre = self.make_rw_attr("PC_TSPRE", Enum(Prescaler))
        self.dir = self.make_rw_attr("PC_DIR", Enum(Direction))

        # =====================================================================
        # Arm Configuration
        # =====================================================================
        self.arm_sel = self.make_rw_attr("PC_ARM_SEL", Enum(ArmSelection))
        self.arm_inp = self.make_rw_attr("PC_ARM_INP", Enum(SysBus))

        self.arm_out = AttrR(Bool())

        # =====================================================================
        # Gate Configuration
        # =====================================================================
        self.gate_sel = self.make_rw_attr("PC_GATE_SEL", Enum(SourceSelection))
        self.gate_inp = self.make_rw_attr("PC_GATE_INP", Enum(SysBus))

        gate_start_reg = REGISTERS_32BIT_BY_NAME["PC_GATE_START"]
        self.gate_start = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=gate_start_reg.address_lo,
                is_32bit=True,
                register_hi=gate_start_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        gate_wid_reg = REGISTERS_32BIT_BY_NAME["PC_GATE_WID"]
        self.gate_wid = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=gate_wid_reg.address_lo,
                is_32bit=True,
                register_hi=gate_wid_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        gate_ngate_reg = REGISTERS_32BIT_BY_NAME["PC_GATE_NGATE"]
        self.gate_ngate = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=gate_ngate_reg.address_lo,
                is_32bit=True,
                register_hi=gate_ngate_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        gate_step_reg = REGISTERS_32BIT_BY_NAME["PC_GATE_STEP"]
        self.gate_step = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=gate_step_reg.address_lo,
                is_32bit=True,
                register_hi=gate_step_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        self.gate_out = AttrR(Bool())

        # =====================================================================
        # Pulse Configuration
        # =====================================================================
        self.pulse_sel = self.make_rw_attr("PC_PULSE_SEL", Enum(SourceSelection))
        self.pulse_inp = self.make_rw_attr("PC_PULSE_INP", Enum(SysBus))

        pulse_start_reg = REGISTERS_32BIT_BY_NAME["PC_PULSE_START"]
        self.pulse_start = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=pulse_start_reg.address_lo,
                is_32bit=True,
                register_hi=pulse_start_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        pulse_wid_reg = REGISTERS_32BIT_BY_NAME["PC_PULSE_WID"]
        self.pulse_wid = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=pulse_wid_reg.address_lo,
                is_32bit=True,
                register_hi=pulse_wid_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        pulse_step_reg = REGISTERS_32BIT_BY_NAME["PC_PULSE_STEP"]
        self.pulse_step = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=pulse_step_reg.address_lo,
                is_32bit=True,
                register_hi=pulse_step_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        pulse_max_reg = REGISTERS_32BIT_BY_NAME["PC_PULSE_MAX"]
        self.pulse_max = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=pulse_max_reg.address_lo,
                is_32bit=True,
                register_hi=pulse_max_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        pulse_dly_reg = REGISTERS_32BIT_BY_NAME["PC_PULSE_DLY"]
        self.pulse_dly = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=pulse_dly_reg.address_lo,
                is_32bit=True,
                register_hi=pulse_dly_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        self.pulse_out = AttrR(Bool())

        # =====================================================================
        # Capture Configuration and Status
        # =====================================================================
        self.bit_cap = self.make_rw_attr("PC_BIT_CAP", Int())

        num_cap_reg = REGISTERS_32BIT_BY_NAME["PC_NUM_CAP"]
        self.num_cap = AttrR(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=num_cap_reg.address_lo,
                is_32bit=True,
                register_hi=num_cap_reg.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        # =====================================================================
        # Last Captured Values (updated by interrupts, no IO)
        # =====================================================================
        self.time_last = AttrR(Int())
        self.enc1_last = AttrR(Int())
        self.enc2_last = AttrR(Int())
        self.enc3_last = AttrR(Int())
        self.enc4_last = AttrR(Int())

    def register_interrupt_handler(self, handler: "InterruptHandler") -> None:
        """Register interrupt handler to receive bit_cap updates.

        This method sets up a callback so that when the bit_cap register
        changes, the interrupt handler is notified and can correctly parse
        incoming position compare data messages.

        Args:
            handler: The interrupt handler to notify of bit_cap changes
        """
        self._interrupt_handler = handler

        # Set up callback to update interrupt handler when bit_cap changes
        async def on_bit_cap_update(value: int | None) -> None:
            """Update interrupt handler when PC_BIT_CAP changes."""
            if value is not None and self._interrupt_handler is not None:
                self._interrupt_handler.set_bit_cap(value)

        self.bit_cap.add_on_update_callback(on_bit_cap_update)

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """
        # Update status from system bus
        # PC_ARM is index 29 (in sys_stat1)
        # PC_GATE is index 30 (in sys_stat1)
        # PC_PULSE is index 31 (in sys_stat1)
        await self.arm_out.update(bool((sys_stat1 >> 29) & 1))
        await self.gate_out.update(bool((sys_stat1 >> 30) & 1))
        await self.pulse_out.update(bool((sys_stat1 >> 31) & 1))

    @command()
    async def arm(self) -> None:
        """Arm position compare acquisition.

        This sends the PC_ARM command to start data acquisition.
        The Zebra will respond with a PR interrupt to indicate buffers are reset.
        """
        # The actual command is handled by the parent controller
        # This is a placeholder for command routing
        pass

    @command()
    async def disarm(self) -> None:
        """Disarm position compare acquisition.

        This sends the PC_DISARM command to stop data acquisition.
        The Zebra will respond with a PX interrupt to indicate completion.
        """
        # The actual command is handled by the parent controller
        # This is a placeholder for command routing
        pass
