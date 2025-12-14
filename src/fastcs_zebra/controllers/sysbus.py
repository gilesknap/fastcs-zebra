"""System bus status bit controllers.

Provides individual boolean indicators for all 64 system bus signals,
organized into two sub-controllers (SysBus1 for bits 0-31, SysBus2 for bits 32-63).
These are derived from the sys_stat1 and sys_stat2 registers and updated via callbacks.
"""

from fastcs.attributes import AttrR
from fastcs.controllers import Controller
from fastcs.datatypes import Bool

from fastcs_zebra.registers import SysBus


class SysBus1Controller(Controller):
    """Controller for system bus signals 0-31 (sys_stat1).

    Provides individual boolean indicators for the first 32 system bus signals.
    These are read-only attributes that reflect the current state of each signal.

    Attributes are named after the SysBus enum values (lowercase):
        disconnect, in1_ttl, in1_nim, in1_lvds, in2_ttl, in2_nim, in2_lvds,
        in3_ttl, in3_oc, in3_lvds, in4_ttl, in4_cmp, in4_pecl,
        in5_enca, in5_encb, in5_encz, in5_conn, in6_enca, in6_encb, in6_encz, in6_conn,
        in7_enca, in7_encb, in7_encz, in7_conn, in8_enca, in8_encb, in8_encz, in8_conn,
        pc_arm, pc_gate, pc_pulse
    """

    def __init__(self):
        """Initialize system bus 1 controller with bits 0-31."""
        super().__init__()

        # Create boolean attributes for bits 0-31
        for signal in SysBus:
            if signal.value < 32:
                attr_name = signal.name.lower()
                setattr(self, attr_name, AttrR(Bool()))


class SysBus2Controller(Controller):
    """Controller for system bus signals 32-63 (sys_stat2).

    Provides individual boolean indicators for the second 32 system bus signals.
    These are read-only attributes that reflect the current state of each signal.

    Attributes are named after the SysBus enum values (lowercase):
        and1, and2, and3, and4, or1, or2, or3, or4,
        gate1, gate2, gate3, gate4,
        div1_outd, div2_outd, div3_outd, div4_outd,
        div1_outn, div2_outn, div3_outn, div4_outn,
        pulse1, pulse2, pulse3, pulse4,
        quad_outa, quad_outb,
        clock_1khz, clock_1mhz,
        soft_in1, soft_in2, soft_in3, soft_in4
    """

    def __init__(self):
        """Initialize system bus 2 controller with bits 32-63."""
        super().__init__()
