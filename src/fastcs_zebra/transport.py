"""Asyncio serial transport for Zebra hardware communication."""

import asyncio
import logging

try:
    import aioserial
except ImportError:
    aioserial = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ZebraTransport:
    """Asyncio-based serial transport for Zebra hardware.

    Provides low-level serial communication with the Zebra device using
    asyncio for non-blocking I/O. Handles connection management, line-based
    reading/writing, and proper cleanup.

    The Zebra uses:
    - 115200 baud, 8N1, no flow control
    - Newline (\\n) line termination
    - ASCII text protocol
    """

    BAUD_RATE = 115200
    TIMEOUT = 1.0

    def __init__(self, port: str):
        """Initialize transport for given serial port.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0', 'COM3')
        """
        if aioserial is None:
            raise ImportError(
                "aioserial is required for serial communication. "
                "Install with: pip install aioserial"
            )

        self.port = port
        self._serial: aioserial.AioSerial | None = None  # type: ignore[name-defined]
        self._connected = False

    async def connect(self) -> None:
        """Open serial connection to Zebra hardware.

        Raises:
            aioserial.SerialException: If connection fails
        """
        if self._connected:
            logger.warning(f"Already connected to {self.port}")
            return

        logger.info(f"Connecting to Zebra on {self.port} at {self.BAUD_RATE} baud")

        self._serial = aioserial.AioSerial(  # type: ignore[union-attr]
            port=self.port,
            baudrate=self.BAUD_RATE,
            bytesize=aioserial.EIGHTBITS,  # type: ignore[union-attr]
            parity=aioserial.PARITY_NONE,  # type: ignore[union-attr]
            stopbits=aioserial.STOPBITS_ONE,  # type: ignore[union-attr]
            timeout=self.TIMEOUT,
        )

        self._connected = True
        logger.info(f"Connected to Zebra on {self.port}")

    async def disconnect(self) -> None:
        """Close serial connection."""
        if not self._connected:
            return

        logger.info(f"Disconnecting from {self.port}")

        if self._serial:
            self._serial.close()
            self._serial = None

        self._connected = False
        logger.info("Disconnected from Zebra")

    @property
    def connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected and self._serial is not None

    async def write_line(self, data: str) -> None:
        """Write a line of text to the Zebra.

        Automatically appends newline terminator.

        Args:
            data: ASCII text command (without newline)

        Raises:
            RuntimeError: If not connected
        """
        if not self.connected:
            raise RuntimeError("Not connected to Zebra")

        line = data + "\n"
        logger.debug(f"TX: {data!r}")

        await self._serial.write_async(line.encode("ascii"))  # type: ignore[union-attr]

    async def read_line(self, timeout: float | None = None) -> str:
        """Read a line of text from the Zebra.

        Reads until newline terminator, which is stripped from result.

        Args:
            timeout: Read timeout in seconds (uses default if None)

        Returns:
            Received line without newline terminator

        Raises:
            RuntimeError: If not connected
            TimeoutError: If read times out
        """
        if not self.connected:
            raise RuntimeError("Not connected to Zebra")

        if timeout is None:
            timeout = self.TIMEOUT

        try:
            # Read until newline with timeout
            line_bytes = await asyncio.wait_for(
                self._serial.readline_async(),  # type: ignore[union-attr]
                timeout=timeout,
            )

            # Decode and strip newline
            line = line_bytes.decode("ascii").rstrip("\n")
            logger.debug(f"RX: {line!r}")

            return line

        except TimeoutError:
            logger.error(f"Read timeout after {timeout}s")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False
