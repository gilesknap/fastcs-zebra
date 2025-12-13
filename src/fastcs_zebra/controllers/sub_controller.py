"""
A base class for all Zebra Subcontrollers.
"""

from fastcs.controllers import Controller


class ZebraSubcontroller(Controller):
    """Base class for all Zebra Subcontrollers."""

    def __init__(self, ios=None):
        """Initialize Zebra controller.

        Args:
            ios: List of ZebraRegisterIO instances used by this controller.
        """
        super().__init__(ios=ios or [])
