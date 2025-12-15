"""Gate generator sub-controllers (GATE1-4).

Each gate generator is an SR latch with:
- Trigger input (INP1): Rising edge sets output high
- Reset input (INP2): Rising edge resets output low
- Output status: Current gate output state from system bus

Gate generators are useful for creating enable windows that start and stop
based on external signals.
"""

from fastcs.attributes import AttrR
from fastcs.datatypes import Bool, Enum

from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO
from fastcs_zebra.registers import SysBus


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

        self.inp1 = self.make_register(f"GATE{gate_num}_INP1", Enum(SysBus))
        self.inp2 = self.make_register(f"GATE{gate_num}_INP2", Enum(SysBus))

        # System bus index for this gate's output
        self._sysbus_index = getattr(SysBus, f"GATE{gate_num}")

        # Output state (from system bus status)
        self.out = AttrR(Bool())
