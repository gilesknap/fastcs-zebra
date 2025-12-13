"""
A base class for all Zebra Subcontrollers.
"""

from fastcs.controllers import Controller

from fastcs_zebra.register_io import ZebraRegisterIO


class ZebraSubcontroller(Controller):
    """Base class for all Zebra Subcontrollers."""

    count = 0  # Number of subcontrollers available (override in subclasses)

    all_controllers = []  # List of all instantiated subcontrollers

    def __init__(
        self,
        num: int,
        register_io: ZebraRegisterIO,
    ):
        """Initialize Zebra controller.

        Args:
            num: the subcontroller subclass number.
            register_io: the ZebraRegisterIO instance used by this controller.
        """
        super().__init__(ios=[register_io])

        if not 1 <= num <= self.count:
            raise ValueError(f"number must be 1-{self.count}, got {num}")

        self.all_controllers.append(self)
