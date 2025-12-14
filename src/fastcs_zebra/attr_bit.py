"""
A fastcs read-only attribute that reads a single bit from a share io_ref.
"""

from fastcs.attributes.attr_r import AttrR
from fastcs.datatypes import Bool, DataType, Enum, Int

from fastcs_zebra.register_io import ZebraRegisterIO, ZebraRegisterIORef


class AttrBit(AttrR[int]):
    """A read-only attribute that reads a single bit from a shared io_ref.

    This attribute reads a specific bit from an integer value provided by the
    shared io_ref. It is useful for representing boolean flags stored as bits
    within a larger integer register.

    Attributes:
        bit_index: The index of the bit to read (0 for least significant bit).
    """

    def __init__(
        self,
        bit_index: int,
        io_ref: ZebraRegisterIORef,
        group: str | None = None,
        description: str | None = None,
    ):
        """Initialize the AttrBit.

        Args:
            bit_index: The index of the bit to read (0 for least significant bit).
            io_ref: The shared io_ref providing the integer value.
            group: Optional group name for the attribute.
            description: Optional description of the attribute.
        """
        super().__init__(
            datatype=Int(), io_ref=io_ref, group=group, description=description
        )
        self._bit_index = bit_index

    async def update(self, value: int) -> None:
        """Update the value of the attribute by extracting the specified bit.

        Args:
            value: The integer value from which to extract the bit.
        """
        bit_value = (value >> self._bit_index) & 0x1
        await super().update(bit_value)
