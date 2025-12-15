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

from fastcs.attributes import AttrR
from fastcs.datatypes import Bool, Enum, Int

if TYPE_CHECKING:
    from fastcs_zebra.interrupts import InterruptHandler
from fastcs_zebra.controllers.enums import (
    ArmSelection,
    Direction,
    EncoderSelection,
    Prescaler,
    SourceSelection,
)
from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO
from fastcs_zebra.registers import SysBus


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
        self.enc = self.make_register("PC_ENC", Enum(EncoderSelection))
        self.tspre = self.make_register("PC_TSPRE", Enum(Prescaler))
        self.dir = self.make_register("PC_DIR", Enum(Direction))

        # =====================================================================
        # Arm Configuration
        # =====================================================================
        self.arm_sel = self.make_register("PC_ARM_SEL", Enum(ArmSelection))
        self.arm_inp = self.make_register("PC_ARM_INP", Enum(SysBus))

        self.arm_out = AttrR(Bool())

        # =====================================================================
        # Gate Configuration
        # =====================================================================
        self.gate_sel = self.make_register("PC_GATE_SEL", Enum(SourceSelection))
        self.gate_inp = self.make_register("PC_GATE_INP", Enum(SysBus))

        self.gate_start = self.make_register32("PC_GATE_START", Int())
        self.gate_wid = self.make_register32("PC_GATE_WID", Int())
        self.gate_ngate = self.make_register32("PC_GATE_NGATE", Int())
        self.gate_step = self.make_register32("PC_GATE_STEP", Int())

        self.gate_out = AttrR(Bool())

        # =====================================================================
        # Pulse Configuration
        # =====================================================================
        self.pulse_sel = self.make_register("PC_PULSE_SEL", Enum(SourceSelection))
        self.pulse_inp = self.make_register("PC_PULSE_INP", Enum(SysBus))

        self.pulse_start = self.make_register32("PC_PULSE_START", Int())
        self.pulse_wid = self.make_register32("PC_PULSE_WID", Int())
        self.pulse_step = self.make_register32("PC_PULSE_STEP", Int())
        self.pulse_max = self.make_register32("PC_PULSE_MAX", Int())
        self.pulse_dly = self.make_register32("PC_PULSE_DLY", Int())

        self.pulse_out = AttrR(Bool())

        # =====================================================================
        # Capture Configuration and Status
        # =====================================================================
        self.bit_cap = self.make_register("PC_BIT_CAP", Int())

        self.num_cap = self.make_register32("PC_NUM_CAP", Int())

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
