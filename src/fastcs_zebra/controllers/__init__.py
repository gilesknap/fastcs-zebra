"""Zebra sub-controller hierarchy.

This package provides FastCS sub-controllers for each major Zebra subsystem:
- Logic gates (AND1-4, OR1-4)
- Gate generators (GATE1-4)
- Pulse generators (PULSE1-4)
- Pulse dividers (DIV1-4)
- Output routing (OUT1-8)
- Position compare subsystem

Each sub-controller exposes its associated registers as FastCS attributes
and provides system bus status monitoring.
"""

from .dividers import DividerController
from .gates import GateController
from .logic import AndGateController, OrGateController
from .outputs import OutputController
from .position_compare import PositionCompareController
from .pulses import PulseController

__all__ = [
    "AndGateController",
    "DividerController",
    "GateController",
    "OrGateController",
    "OutputController",
    "PositionCompareController",
    "PulseController",
]
