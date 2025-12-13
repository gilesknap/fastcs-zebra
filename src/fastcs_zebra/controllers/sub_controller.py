"""
A base class for all Zebra Subcontrollers.
"""

from fastcs.controllers import Controller

from fastcs_zebra.register_io import ZebraRegisterIO


class ZebraSubcontroller(Controller):
    """Base class for all Zebra Subcontrollers."""

    count = 0  # Number of subcontrollers available (override in subclasses)

    all_controllers: list["ZebraSubcontroller"] = []  # List of all subcontrollers

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

        self._num = num
        self._register_io = register_io

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """
        raise NotImplementedError
