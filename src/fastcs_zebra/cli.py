"""Command-line interface for Zebra serial communication testing.

Provides interactive commands for testing the ZebraTransport and ZebraProtocol
layers against real hardware.
"""

import argparse
import asyncio
import logging
import sys
from typing import NoReturn

from .interrupts import InterruptHandler, PositionCompareData
from .protocol import ZebraProtocol
from .transport import ZebraTransport

logger = logging.getLogger(__name__)


class ZebraCLI:
    """Interactive CLI for Zebra communication.

    Commands:
    - r <addr>: Read register (hex address)
    - w <addr> <value>: Write register (hex addr and value)
    - r32 <addr_lo> <addr_hi>: Read 32-bit register
    - w32 <addr_lo> <addr_hi> <value>: Write 32-bit register
    - save: Save configuration to flash
    - load: Load configuration from flash
    - arm: Arm position compare
    - disarm: Disarm position compare
    - quit: Exit
    """

    def __init__(self, port: str):
        """Initialize CLI.

        Args:
            port: Serial port path
        """
        self.port = port
        self.transport: ZebraTransport | None = None
        self.protocol: ZebraProtocol | None = None
        self.interrupt_handler = InterruptHandler()
        self.running = False
        self._interrupt_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Connect to Zebra and start CLI."""

        # Setup interrupt callbacks
        @self.interrupt_handler.on_reset
        async def on_reset():
            print(">>> Position compare RESET")

        @self.interrupt_handler.on_data
        async def on_data(data: PositionCompareData):
            print(f">>> Data: ts={data.timestamp:#010x}", end="")
            if data.encoder1 is not None:
                print(f" enc1={data.encoder1}", end="")
            if data.encoder2 is not None:
                print(f" enc2={data.encoder2}", end="")
            if data.encoder3 is not None:
                print(f" enc3={data.encoder3}", end="")
            if data.encoder4 is not None:
                print(f" enc4={data.encoder4}", end="")
            print()

        @self.interrupt_handler.on_end
        async def on_end():
            print(">>> Position compare COMPLETE")

        # Connect
        self.transport = ZebraTransport(self.port)
        await self.transport.connect()
        self.protocol = ZebraProtocol(self.transport)

        # Start interrupt monitoring task
        self.running = True
        self._interrupt_task = asyncio.create_task(self._monitor_interrupts())

        print(f"Connected to Zebra on {self.port}")
        print("Type 'help' for available commands")

    async def stop(self) -> None:
        """Disconnect from Zebra."""
        self.running = False

        if self._interrupt_task:
            self._interrupt_task.cancel()
            try:
                await self._interrupt_task
            except asyncio.CancelledError:
                pass

        if self.transport:
            await self.transport.disconnect()

        print("Disconnected")

    async def _monitor_interrupts(self) -> None:
        """Background task to monitor for interrupt messages."""
        while self.running:
            try:
                # Try to read with short timeout
                message = await self.transport.read_line(timeout=0.1)  # type: ignore[union-attr]

                # Check if it's an interrupt
                if message.startswith("P"):
                    await self.interrupt_handler.handle_message(message)
                else:
                    # Not an interrupt, might be a delayed response
                    logger.warning(f"Unexpected message: {message!r}")

            except TimeoutError:
                # No data available, continue
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error monitoring interrupts: {e}")
                await asyncio.sleep(0.1)

    async def run_command(self, cmd_line: str) -> bool:
        """Execute a command.

        Args:
            cmd_line: Command line input

        Returns:
            False if should exit, True otherwise
        """
        parts = cmd_line.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()

        try:
            if cmd in ("quit", "exit", "q"):
                return False

            elif cmd == "help":
                print(self.__class__.__doc__)

            elif cmd == "r" and len(parts) == 2:
                addr = int(parts[1], 16)
                value = await self.protocol.read_register(addr)  # type: ignore[union-attr]
                print(f"R{addr:02X} = {value:#06x} ({value})")

            elif cmd == "w" and len(parts) == 3:
                addr = int(parts[1], 16)
                value = int(parts[2], 16)
                result = await self.protocol.write_register(addr, value)  # type: ignore[union-attr]
                print(f"W{addr:02X} {value:#06x} -> {result:#06x}")

            elif cmd == "r32" and len(parts) == 3:
                addr_lo = int(parts[1], 16)
                addr_hi = int(parts[2], 16)
                value = await self.protocol.read_register_32bit(addr_lo, addr_hi)  # type: ignore[union-attr]
                print(f"R32[{addr_hi:02X}:{addr_lo:02X}] = {value:#010x} ({value})")

            elif cmd == "w32" and len(parts) == 4:
                addr_lo = int(parts[1], 16)
                addr_hi = int(parts[2], 16)
                value = int(parts[3], 16)
                result = await self.protocol.write_register_32bit(  # type: ignore[union-attr]
                    addr_lo, addr_hi, value
                )
                print(
                    f"W32[{addr_hi:02X}:{addr_lo:02X}] {value:#010x} -> {result:#010x}"
                )

            elif cmd == "save":
                await self.protocol.flash_command("S")  # type: ignore[union-attr]
                print("Configuration saved to flash")

            elif cmd == "load":
                await self.protocol.flash_command("L")  # type: ignore[union-attr]
                print("Configuration loaded from flash")

            elif cmd == "arm":
                # Write PC_ARM register (0x8B)
                await self.protocol.write_register(0x8B, 1)  # type: ignore[union-attr]
                print("Position compare armed")

            elif cmd == "disarm":
                # Write PC_DISARM register (0x8C)
                await self.protocol.write_register(0x8C, 1)  # type: ignore[union-attr]
                print("Position compare disarmed")

            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")

        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Command failed: {e}")
            logger.exception("Command error")

        return True

    async def run_interactive(self) -> None:
        """Run interactive command loop."""
        await self.start()

        try:
            while True:
                try:
                    # Get input (in async context we use run_in_executor)
                    loop = asyncio.get_event_loop()
                    cmd_line = await loop.run_in_executor(None, input, "zebra> ")

                    should_continue = await self.run_command(cmd_line)
                    if not should_continue:
                        break

                except EOFError:
                    print()
                    break
                except KeyboardInterrupt:
                    print()
                    break

        finally:
            await self.stop()


async def async_main(args: argparse.Namespace) -> int:
    """Async main entry point.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cli = ZebraCLI(args.port)

    if args.command:
        # Execute single command
        await cli.start()
        try:
            await cli.run_command(" ".join(args.command))
        finally:
            await cli.stop()
        return 0

    # Interactive mode
    await cli.run_interactive()
    return 0


def main(argv: list[str] | None = None) -> NoReturn:
    """Main entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv)
    """
    parser = argparse.ArgumentParser(description="Zebra serial communication test tool")
    parser.add_argument(
        "port",
        help="Serial port (e.g., /dev/ttyUSB0 or COM3)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "-c",
        "--command",
        nargs="+",
        help="Execute single command and exit",
    )

    args = parser.parse_args(argv)

    try:
        exit_code = asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted")
        exit_code = 130

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
