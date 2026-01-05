"""Pulse divider sub-controllers (DIV1-4).

Each pulse divider:
- Takes an input signal from the 64-signal system bus
- Divides the pulse count by a 32-bit divisor
- Provides two outputs:
  - OUTD (divided): Output every N pulses
  - OUTN (not divided): Passthrough of input
"""

from fastcs.attributes import AttrR
from fastcs.datatypes import Bool, Enum, Int

from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO
from fastcs_zebra.registers import SysBus


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

        # System bus indices for this divider's outputs
        self._sysbus_outd = getattr(SysBus, f"DIV{div_num}_OUTD")
        self._sysbus_outn = getattr(SysBus, f"DIV{div_num}_OUTN")

        self.inp = self.make_register(f"DIV{div_num}_INP", Enum(SysBus))
        self.div = self.make_register32(f"DIV{div_num}_DIV", Int())

        # Output states (from system bus status)
        self.outd = AttrR(Bool())  # Divided output
        self.outn = AttrR(Bool())  # Non-divided (passthrough) output
