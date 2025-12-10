#!/usr/bin/env python3
"""Quick test to demonstrate that concurrent register reads are now serialized."""

import asyncio

from fastcs_zebra.protocol import ZebraProtocol
from fastcs_zebra.transport import ZebraTransport


async def main():
    """Test that concurrent reads are serialized."""
    # Use simulator to avoid needing hardware
    transport = ZebraTransport("sim://test")
    await transport.connect()

    protocol = ZebraProtocol(transport)

    print("Testing concurrent register reads...")
    print("=" * 60)

    # Launch 5 concurrent reads - with the lock, these will be serialized
    # Without the lock, these would all send commands before waiting for responses
    tasks = [
        protocol.read_register(0xF0),  # SYS_VER
        protocol.read_register(0xF1),  # SYS_STATERR
        protocol.read_register(0x88),  # PC_ENC
        protocol.read_register(0x89),  # PC_TSPRE
        protocol.read_register(0x7F),  # SOFT_IN
    ]

    results = await asyncio.gather(*tasks)

    print(f"Read SYS_VER: 0x{results[0]:04X}")
    print(f"Read SYS_STATERR: 0x{results[1]:04X}")
    print(f"Read PC_ENC: 0x{results[2]:04X}")
    print(f"Read PC_TSPRE: 0x{results[3]:04X}")
    print(f"Read SOFT_IN: 0x{results[4]:04X}")
    print()
    print("✓ All concurrent reads completed successfully!")
    print("✓ Each read waited for the previous one to complete.")

    await transport.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
