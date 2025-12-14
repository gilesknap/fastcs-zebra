"""Logic gate sub-controllers (AND1-4, OR1-4).

Each logic gate has:
- 4 input multiplexers (select from 64 system bus signals)
- 4 enable bits (enable/disable each input)
- 4 inversion bits (invert each input before the gate operation)
- 1 output status (current gate output state from system bus)

The gate output is available on the system bus for routing to outputs
or other gates.
"""

from fastcs.attributes import AttrR
from fastcs.datatypes import Bool, Enum, Int

from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO
from fastcs_zebra.registers import SysBus


class AndGateController(ZebraSubcontroller):
    """Controller for a single AND gate (AND1-AND4).

    The AND gate combines up to 4 inputs with AND logic. Each input can be:
    - Enabled/disabled via the enable mask
    - Inverted before the AND operation
    - Selected from any of the 64 system bus signals

    Attributes:
        ena_b0-b3: Enable bits for inputs 1-4
        inv_b0-b3: Inversion bits for inputs 1-4
        inp1-4: Input source selection (0-63 system bus index)
        inp1-4_str: Human-readable name of selected input
        out: Current output state of the AND gate
    """

    count = 4  # Number of AND gates available

    def __init__(
        self,
        gate_num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize AND gate controller.

        Args:
            gate_num: Gate number (1-4)
            register_io: Shared register IO handler
        """
        super().__init__(gate_num, register_io)

        self.inv = self.make_register(f"AND{gate_num}_INV", Int())
        self.ena = self.make_register(f"AND{gate_num}_ENA", Int())
        self.inp1 = self.make_register(f"AND{gate_num}_INP1", Enum(SysBus))
        self.inp2 = self.make_register(f"AND{gate_num}_INP2", Enum(SysBus))
        self.inp3 = self.make_register(f"AND{gate_num}_INP3", Enum(SysBus))
        self.inp4 = self.make_register(f"AND{gate_num}_INP4", Enum(SysBus))

        # System bus index for this gate's output
        self._sysbus_index = getattr(SysBus, f"AND{gate_num}")

        # Output state (from system bus status)
        self.out = AttrR(Bool())

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """

        # Update output state from system bus
        # AND gates are indices 32-35 (in sys_stat2)
        bit_index = self._sysbus_index - 32
        out_state = bool((sys_stat2 >> bit_index) & 1)
        await self.out.update(out_state)


class OrGateController(ZebraSubcontroller):
    """Controller for a single OR gate (OR1-OR4).

    The OR gate combines up to 4 inputs with OR logic. Each input can be:
    - Enabled/disabled via the enable mask
    - Inverted before the OR operation
    - Selected from any of the 64 system bus signals

    Attributes:
        ena_b0-b3: Enable bits for inputs 1-4
        inv_b0-b3: Inversion bits for inputs 1-4
        inp1-4: Input source selection (0-63 system bus index)
        inp1-4_str: Human-readable name of selected input
        out: Current output state of the OR gate
    """

    count = 4  # Number of OR gates available

    def __init__(
        self,
        gate_num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize OR gate controller.

        Args:
            gate_num: Gate number (1-4)
            register_io: Shared register IO handler
        """
        super().__init__(gate_num, register_io)

        self.inv = self.make_register(f"OR{gate_num}_INV", Int())
        self.ena = self.make_register(f"OR{gate_num}_ENA", Int())
        self.inp1 = self.make_register(f"OR{gate_num}_INP1", Enum(SysBus))
        self.inp2 = self.make_register(f"OR{gate_num}_INP2", Enum(SysBus))
        self.inp3 = self.make_register(f"OR{gate_num}_INP3", Enum(SysBus))
        self.inp4 = self.make_register(f"OR{gate_num}_INP4", Enum(SysBus))

        # System bus index for this gate's output
        self._sysbus_index = getattr(SysBus, f"OR{gate_num}")

        # Output state (from system bus status)
        self.out = AttrR(Bool())

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """

        # Update output state from system bus
        # OR gates are indices 36-39 (in sys_stat2)
        bit_index = self._sysbus_index - 32
        out_state = bool((sys_stat2 >> bit_index) & 1)
        await self.out.update(out_state)
