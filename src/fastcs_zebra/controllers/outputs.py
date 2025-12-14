"""Output routing sub-controllers (OUT1-8).

The Zebra has 8 output connectors with different signal types:
- OUT1-OUT2: TTL, NIM, LVDS
- OUT3: TTL, OC (open collector), LVDS
- OUT4: TTL, NIM, PECL
- OUT5-OUT8: Encoder outputs (ENCA, ENCB, ENCZ, CONN enable)

Each output type can be independently routed to any of the 64 system bus signals.
"""

from fastcs.datatypes import Enum

from fastcs_zebra.controllers.sub_controller import ZebraSubcontroller
from fastcs_zebra.register_io import ZebraRegisterIO
from fastcs_zebra.registers import SysBus


class OutputController(ZebraSubcontroller):
    """Controller for a single output connector (OUT1-OUT8).

    Output connectors have different signal types depending on the connector:
    - OUT1-OUT2: TTL, NIM, LVDS
    - OUT3: TTL, OC (open collector), LVDS
    - OUT4: TTL, NIM, PECL
    - OUT5-OUT8: ENCA, ENCB, ENCZ, CONN (encoder outputs)

    Attributes vary by output type. Each signal type has:
    - A value attribute (0-63 system bus index)
    - A string attribute showing the human-readable signal name
    """

    # Define the signal types for each output
    OUTPUT_TYPES = {
        1: ["ttl", "nim", "lvds"],
        2: ["ttl", "nim", "lvds"],
        3: ["ttl", "oc", "lvds"],
        4: ["ttl", "nim", "pecl"],
        5: ["enca", "encb", "encz", "conn"],
        6: ["enca", "encb", "encz", "conn"],
        7: ["enca", "encb", "encz", "conn"],
        8: ["enca", "encb", "encz", "conn"],
    }

    count = 8  # Number of outputs available

    def __init__(
        self,
        out_num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize output controller.

        Args:
            out_num: Output number (1-8)
            register_io: Shared register IO handler
        """
        super().__init__(out_num, register_io)

        self._signal_types = self.OUTPUT_TYPES[out_num]

        # Create attributes for each signal type
        for sig_type in self._signal_types:
            reg_name = f"OUT{out_num}_{sig_type.upper()}"
            attr = self.make_rw_attr(reg_name, Enum(SysBus))
            setattr(self, sig_type, attr)

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """
        # Update string representations for each signal type
        pass
