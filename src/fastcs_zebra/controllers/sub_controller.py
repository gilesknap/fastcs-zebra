"""
A base class for all Zebra Subcontrollers.
"""

from fastcs.attributes import AttrRW
from fastcs.controllers import Controller

from fastcs_zebra.constants import SLOW_UPDATE
from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import REGISTERS_BY_NAME


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

    def make_rw_attr(
        self,
        register_name: str,
        dtype,
        update_period: float = SLOW_UPDATE,
    ) -> AttrRW:
        """Helper to create a read-write attribute with ZebraRegisterIORef"""
        addr = REGISTERS_BY_NAME[register_name].address
        io_ref = ZebraRegisterIORef(update_period=update_period, register=addr)
        attr = AttrRW(datatype=dtype, io_ref=io_ref)
        return attr

    async def update_derived_values(self, sys_stat1: int, sys_stat2: int) -> None:
        """Update derived values from system bus status.

        Args:
            sys_stat1: System bus status bits 0-31
            sys_stat2: System bus status bits 32-63
        """
        raise NotImplementedError
