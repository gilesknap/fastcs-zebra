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

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command

from fastcs_zebra.attr_register import AttrSourceRegister
from fastcs_zebra.constants import SLOW_UPDATE
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import (
    REGISTERS_32BIT_BY_NAME,
    REGISTERS_BY_NAME,
)

# Prescaler values and their meanings
PRESCALER_VALUES = {
    500000: "10s",  # Time unit = 10 seconds
    5000: "s",  # Time unit = seconds
    5: "ms",  # Time unit = milliseconds
}

# Source selection values
SOURCE_SEL = {
    0: "Position",
    1: "Time",
    2: "External",
}

# Arm selection values
ARM_SEL = {
    0: "Software",
    1: "External",
}

# Direction values
DIRECTION = {
    0: "Positive",
    1: "Negative",
}

# Encoder selection values
ENCODER_SEL = {
    0: "Enc1",
    1: "Enc2",
    2: "Enc3",
    3: "Enc4",
    4: "Enc1+2+3+4",
}


class PositionCompareController(Controller):
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

        # Last captured values (updated by interrupts)
        time_last: Last captured timestamp
        enc1_last - enc4_last: Last captured encoder values
    """

    def __init__(
        self,
        register_io: ZebraRegisterIO,
    ):
        """Initialize position compare controller.

        Args:
            register_io: Shared register IO handler
        """
        self._register_io = register_io

        super().__init__(ios=[register_io])

        # =====================================================================
        # Encoder and Timing Selection
        # =====================================================================
        self.enc_str = AttrR(String())
        self.enc = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_ENC"].address, update_period=SLOW_UPDATE
            ),
            str_attr=self.enc_str,
        )

        self.tspre_str = AttrR(String())
        self.tspre = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_TSPRE"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.tspre_str,
        )

        self.dir_str = AttrR(String())
        self.dir = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_DIR"].address, update_period=SLOW_UPDATE
            ),
            str_attr=self.dir_str,
        )

        # =====================================================================
        # Arm Configuration
        # =====================================================================
        self.arm_sel_str = AttrR(String())
        self.arm_sel = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_ARM_SEL"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.arm_sel_str,
        )

        self.arm_inp_str = AttrR(String())
        self.arm_inp = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_ARM_INP"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.arm_inp_str,
        )

        self.arm_out = AttrR(Bool())

        # =====================================================================
        # Gate Configuration
        # =====================================================================
        self.gate_sel_str = AttrR(String())
        self.gate_sel = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_GATE_SEL"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.gate_sel_str,
        )

        self.gate_inp_str = AttrR(String())
        self.gate_inp = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_GATE_INP"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.gate_inp_str,
        )

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
        self.pulse_sel_str = AttrR(String())
        self.pulse_sel = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_PULSE_SEL"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.pulse_sel_str,
        )

        self.pulse_inp_str = AttrR(String())
        self.pulse_inp = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_PULSE_INP"].address,
                update_period=SLOW_UPDATE,
            ),
            str_attr=self.pulse_inp_str,
        )

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
        self.bit_cap = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=REGISTERS_BY_NAME["PC_BIT_CAP"].address,
                update_period=SLOW_UPDATE,
            ),
        )

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
