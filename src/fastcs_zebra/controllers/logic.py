"""Logic gate sub-controllers (AND1-4, OR1-4).

Each logic gate has:
- 4 input multiplexers (select from 64 system bus signals)
- 4 enable bits (enable/disable each input)
- 4 inversion bits (invert each input before the gate operation)
- 1 output status (current gate output state from system bus)

The gate output is available on the system bus for routing to outputs
or other gates.
"""

from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String

from fastcs_zebra.attr_register import AttrSourceRegister
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import (
    REGISTERS_BY_NAME,
    SysBus,
)


class AndGateController(Controller):
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
        if not 1 <= gate_num <= 4:
            raise ValueError(f"AND gate number must be 1-4, got {gate_num}")

        self._gate_num = gate_num
        self._register_io = register_io

        # Get register addresses for this gate
        inv_reg = REGISTERS_BY_NAME[f"AND{gate_num}_INV"]
        ena_reg = REGISTERS_BY_NAME[f"AND{gate_num}_ENA"]
        inp1_reg = REGISTERS_BY_NAME[f"AND{gate_num}_INP1"]
        inp2_reg = REGISTERS_BY_NAME[f"AND{gate_num}_INP2"]
        inp3_reg = REGISTERS_BY_NAME[f"AND{gate_num}_INP3"]
        inp4_reg = REGISTERS_BY_NAME[f"AND{gate_num}_INP4"]

        # System bus index for this gate's output
        self._sysbus_index = getattr(SysBus, f"AND{gate_num}")

        super().__init__(ios=[register_io])

        # Inversion mask (4-bit bitfield)
        self.inv = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=inv_reg.address, update_period=1.0),
        )

        # Enable mask (4-bit bitfield)
        self.ena = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=ena_reg.address, update_period=1.0),
        )

        # Input 1 source (MUX register, 0-63)
        self.inp1_str = AttrR(String())
        self.inp1 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp1_reg.address, update_period=10.0),
            str_attr=self.inp1_str,
        )

        # Input 2 source
        self.inp2_str = AttrR(String())
        self.inp2 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp2_reg.address, update_period=10.0),
            str_attr=self.inp2_str,
        )

        # Input 3 source
        self.inp3_str = AttrR(String())
        self.inp3 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp3_reg.address, update_period=10.0),
            str_attr=self.inp3_str,
        )
        # Input 4 source
        self.inp4_str = AttrR(String())
        self.inp4 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp4_reg.address, update_period=10.0),
            str_attr=self.inp4_str,
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
        # AND gates are indices 32-35 (in sys_stat2)
        bit_index = self._sysbus_index - 32
        out_state = bool((sys_stat2 >> bit_index) & 1)
        await self.out.update(out_state)


class OrGateController(Controller):
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
        if not 1 <= gate_num <= 4:
            raise ValueError(f"OR gate number must be 1-4, got {gate_num}")

        self._gate_num = gate_num
        self._register_io = register_io

        # Get register addresses for this gate
        inv_reg = REGISTERS_BY_NAME[f"OR{gate_num}_INV"]
        ena_reg = REGISTERS_BY_NAME[f"OR{gate_num}_ENA"]
        inp1_reg = REGISTERS_BY_NAME[f"OR{gate_num}_INP1"]
        inp2_reg = REGISTERS_BY_NAME[f"OR{gate_num}_INP2"]
        inp3_reg = REGISTERS_BY_NAME[f"OR{gate_num}_INP3"]
        inp4_reg = REGISTERS_BY_NAME[f"OR{gate_num}_INP4"]

        # System bus index for this gate's output
        self._sysbus_index = getattr(SysBus, f"OR{gate_num}")

        super().__init__(ios=[register_io])

        # Inversion mask (4-bit bitfield)
        self.inv = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=inv_reg.address, update_period=1.0),
        )

        # Enable mask (4-bit bitfield)
        self.ena = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(register=ena_reg.address, update_period=1.0),
        )

        # Input 1 source (MUX register, 0-63)
        self.inp1_str = AttrR(String())
        self.inp1 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp1_reg.address, update_period=10.0),
            str_attr=self.inp1_str,
        )

        # Input 2 source
        self.inp2_str = AttrR(String())
        self.inp2 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp2_reg.address, update_period=10.0),
            str_attr=self.inp2_str,
        )

        # Input 3 source
        self.inp3_str = AttrR(String())
        self.inp3 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp3_reg.address, update_period=10.0),
            str_attr=self.inp3_str,
        )

        # Input 4 source
        self.inp4_str = AttrR(String())
        self.inp4 = AttrSourceRegister(
            Int(),
            io_ref=ZebraRegisterIORef(register=inp4_reg.address, update_period=10.0),
            str_attr=self.inp4_str,
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
        # OR gates are indices 36-39 (in sys_stat2)
        bit_index = self._sysbus_index - 32
        out_state = bool((sys_stat2 >> bit_index) & 1)
        await self.out.update(out_state)
