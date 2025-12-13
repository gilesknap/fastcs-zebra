"""Pulse divider sub-controllers (DIV1-4).

Each pulse divider:
- Takes an input signal from the 64-signal system bus
- Divides the pulse count by a 32-bit divisor
- Provides two outputs:
  - OUTD (divided): Output every N pulses
  - OUTN (not divided): Passthrough of input
"""

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String

from fastcs_zebra.attr_register import AttrSourceRegister
from fastcs_zebra.constants import SLOW_UPDATE
from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import (
    REGISTERS_32BIT_BY_NAME,
    REGISTERS_BY_NAME,
    SysBus,
)


class DividerController(ZebraSubcontroller):
    """Controller for a single pulse divider (DIV1-DIV4).

    The pulse divider counts input pulses and outputs every Nth pulse,
    where N is the divisor value.

    Attributes:
        inp: Input source (0-63 system bus index)
        inp_str: Human-readable name of input source
        div: Division factor (32-bit value)
        outd: Current state of divided output
        outn: Current state of non-divided (passthrough) output
    """

    count = 4  # Number of dividers available

    def __init__(
        self,
        div_num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize divider controller.

        Args:
            div_num: Divider number (1-4)
            register_io: Shared register IO handler
        """
        super().__init__(div_num, register_io)

        # Get register addresses for this divider
        inp_reg = REGISTERS_BY_NAME[f"DIV{div_num}_INP"]
        div_reg32 = REGISTERS_32BIT_BY_NAME[f"DIV{div_num}_DIV"]

        # System bus indices for this divider's outputs
        self._sysbus_outd = getattr(SysBus, f"DIV{div_num}_OUTD")
        self._sysbus_outn = getattr(SysBus, f"DIV{div_num}_OUTN")

        # Input source (MUX register, 0-63)
        self.inp_str = AttrR(String())
        self.inp = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp_reg.address, update_period=20.0),
            str_attr=self.inp_str,
        )

        # Divisor (32-bit value)
        self.div = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=div_reg32.address_lo,
                is_32bit=True,
                register_hi=div_reg32.address_hi,
                update_period=SLOW_UPDATE,
            ),
        )

        # Output states (from system bus status)
        self.outd = AttrR(Bool())  # Divided output
        self.outn = AttrR(Bool())  # Non-divided (passthrough) output

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """

        # Update output states from system bus
        # DIV OUTD are indices 44-47 (in sys_stat2)
        # DIV OUTN are indices 48-51 (in sys_stat2)
        outd_bit = self._sysbus_outd - 32
        outn_bit = self._sysbus_outn - 32
        await self.outd.update(bool((sys_stat2 >> outd_bit) & 1))
        await self.outn.update(bool((sys_stat2 >> outn_bit) & 1))
