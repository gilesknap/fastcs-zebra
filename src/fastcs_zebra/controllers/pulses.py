"""Pulse generator sub-controllers (PULSE1-4).

Each pulse generator creates a timed pulse with configurable:
- Input trigger source (from 64 system bus signals)
- Delay from trigger to pulse start
- Pulse width
- Prescaler (time unit: 10s, s, or ms)

The pulse output is available on the system bus for routing to outputs
or other logic.
"""

from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import Bool, Enum, Int

from fastcs_zebra.constants import SLOW_UPDATE
from fastcs_zebra.controllers.enums import Prescaler
from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import (
    REGISTERS_BY_NAME,
    SysBus,
)


class PulseController(ZebraSubcontroller):
    """Controller for a single pulse generator (PULSE1-PULSE4).

    The pulse generator creates a single pulse output:
    - Triggered by a rising edge on the input
    - After a configurable delay
    - With a configurable width
    - Time units set by prescaler

    Attributes:
        inp: Input trigger source (0-63 system bus index)
        inp_str: Human-readable name of input source
        dly: Delay from trigger to pulse start (in time units)
        wid: Pulse width (in time units)
        pre: Prescaler value (5=ms, 5000=s, 500000=10s)
        pre_str: Human-readable prescaler string
        out: Current output state of the pulse generator
    """

    count = 4  # Number of pulse generators available

    def __init__(
        self,
        pulse_num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize pulse generator controller.

        Args:
            pulse_num: Pulse generator number (1-4)
            register_io: Shared register IO handler
        """
        super().__init__(pulse_num, register_io)

        # Get register addresses for this pulse generator
        inp_reg = REGISTERS_BY_NAME[f"PULSE{pulse_num}_INP"]
        dly_reg = REGISTERS_BY_NAME[f"PULSE{pulse_num}_DLY"]
        wid_reg = REGISTERS_BY_NAME[f"PULSE{pulse_num}_WID"]
        pre_reg = REGISTERS_BY_NAME[f"PULSE{pulse_num}_PRE"]

        # System bus index for this pulse generator's output
        self._sysbus_index = getattr(SysBus, f"PULSE{pulse_num}")

        # Input source (MUX register, 0-63)
        self.inp = AttrRW(
            Enum(SysBus),
            io_ref=ZebraRegisterIORef(
                register=inp_reg.address, update_period=SLOW_UPDATE
            ),
        )

        # Delay (time from trigger to pulse start)
        self.dly = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=dly_reg.address, update_period=SLOW_UPDATE
            ),
        )

        # Width (pulse duration)
        self.wid = AttrRW(
            Int(),
            io_ref=ZebraRegisterIORef(
                register=wid_reg.address, update_period=SLOW_UPDATE
            ),
        )

        # Prescaler (time unit selection)
        self.pre = AttrRW(
            Enum(Prescaler),
            io_ref=ZebraRegisterIORef(
                register=pre_reg.address, update_period=SLOW_UPDATE
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
        # PULSE generators are indices 52-55 (in sys_stat2)
        bit_index = self._sysbus_index - 32
        out_state = bool((sys_stat2 >> bit_index) & 1)
        await self.out.update(out_state)
