"""
Defines a fastcs read-write attribute that has a related string attribute
derived from its integer value.

Used for specifying input sources by index, with a human-readable name.
"""

from fastcs.attributes import AttrR, AttrRW

from fastcs_zebra.registers import signal_index_to_name


class AttrNamedRegister(AttrRW[int]):
    """A read-write integer attribute representing a register with a descriptive
    string value held in a separate AttrR[str].
    """

    def __init__(self, *args, str_attr: "AttrR[str]", **kwargs):
        """
        Args:
            str_attr: The string attribute to update when this attribute changes.
            *args: Positional arguments for the base AttrRW class.
            **kwargs: Keyword arguments for the base AttrRW class.
        """
        super().__init__(*args, **kwargs)
        self._str_attr = str_attr
        self.add_on_update_callback(self.update_str_attr)

    async def put(self, setpoint: int, sync_setpoint: bool = False) -> None:
        """Update the derived string immediately on put."""

        await self._str_attr.update(signal_index_to_name(setpoint))
        await super().put(setpoint, sync_setpoint)

    async def update_str_attr(self, value: int | None) -> None:
        """Update the derived string on init/change from zebra.

        Args:
            value: The integer value, or None if not yet initialized.
        """
        if value is None:
            await self._str_attr.update("")
        else:
            await self._str_attr.update(signal_index_to_name(value))
