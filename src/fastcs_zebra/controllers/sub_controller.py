"""
A base class for all Zebra Subcontrollers.
"""

from fastcs.attributes import AttrRW
from fastcs.controllers import Controller
from fastcs.util import ONCE

from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef
from fastcs_zebra.registers import REGISTERS_32BIT_BY_NAME, REGISTERS_BY_NAME


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

    def make_register(
        self,
        register_name: str,
        dtype,
        update_period: float = ONCE,
    ) -> AttrRW:
        """Helper to create a read-write attribute with for a register"""
        addr = REGISTERS_BY_NAME[register_name].address
        io_ref = ZebraRegisterIORef(update_period=update_period, register=addr)
        attr = AttrRW(datatype=dtype, io_ref=io_ref)
        return attr

    def make_register32(
        self,
        register_name: str,
        dtype,
        update_period: float = ONCE,
    ) -> AttrRW:
        """Helper to create a read-write attribute with for a register"""
        reg32 = REGISTERS_32BIT_BY_NAME[register_name]
        io_ref = ZebraRegisterIORef(
            update_period=update_period,
            register=reg32.address_lo,
            is_32bit=True,
            register_hi=reg32.address_hi,
        )
        attr = AttrRW(datatype=dtype, io_ref=io_ref)
        return attr
