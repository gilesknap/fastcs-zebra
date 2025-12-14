"""Gate generator sub-controllers (GATE1-4).

Each gate generator is an SR latch with:
- Trigger input (INP1): Rising edge sets output high
- Reset input (INP2): Rising edge resets output low
- Output status: Current gate output state from system bus

Gate generators are useful for creating enable windows that start and stop
based on external signals.
"""

from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import Bool, Enum, Int

from fastcs_zebra.constants import SLOW_UPDATE
from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import (
    REGISTERS_BY_NAME,
    SysBus,
)


class GateController(ZebraSubcontroller):
    """Controller for a single gate generator (GATE1-GATE4).

    The gate generator is an SR latch:
    - Rising edge on INP1 (trigger) sets output HIGH
    - Rising edge on INP2 (reset) sets output LOW

    This is useful for creating enable windows controlled by external signals.

    Attributes:
        inp1: Trigger input source (0-63 system bus index)
        inp1_str: Human-readable name of trigger input
        inp2: Reset input source (0-63 system bus index)
        inp2_str: Human-readable name of reset input
        out: Current output state of the gate generator
    """

    count = 4  # Number of gate generators available

    def __init__(
        self,
        gate_num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize gate generator controller.

        Args:
            gate_num: Gate number (1-4)
            register_io: Shared register IO handler
        """
        super().__init__(gate_num, register_io)

        # Get register addresses for this gate
        inp1_reg = REGISTERS_BY_NAME[f"GATE{gate_num}_INP1"]
        inp2_reg = REGISTERS_BY_NAME[f"GATE{gate_num}_INP2"]

        # System bus index for this gate's output
        self._sysbus_index = getattr(SysBus, f"GATE{gate_num}")

        # Trigger input (INP1) - rising edge sets output high
        self.inp1 = AttrRW(
            Enum(SysBus),
            io_ref=ZebraRegisterIORef(
                register=inp1_reg.address, update_period=SLOW_UPDATE
            ),
        )

        # Reset input (INP2) - rising edge resets output low
        self.inp2 = AttrRW(
            Enum(SysBus),
            io_ref=ZebraRegisterIORef(
                register=inp2_reg.address, update_period=SLOW_UPDATE
            ),
        )

        # Output state (from system bus status)
        self.out = AttrR(Bool())

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """

        # Update output state from system bus
        # GATE generators are indices 40-43 (in sys_stat2)
        bit_index = self._sysbus_index - 32
        out_state = bool((sys_stat2 >> bit_index) & 1)
        await self.out.update(out_state)
