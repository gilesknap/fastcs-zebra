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

    Supports simulation mode: Use port="sim://name" to use software simulator
    instead of real hardware.

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
                  or 'sim://name' for simulator
        """
        self.port = port
        self._is_simulation = port.startswith("sim://")
        self._serial: aioserial.AioSerial | None = None  # type: ignore[name-defined]
        self._connected = False

        # Simulation mode components
        self._simulator = None
        self._sim_rx_queue: asyncio.Queue[str] | None = None
        self._sim_tx_queue: asyncio.Queue[str] | None = None

        if not self._is_simulation and aioserial is None:
            raise ImportError(
                "aioserial is required for serial communication. "
                "Install with: pip install aioserial"
            )

    async def connect(self) -> None:
        """Open serial connection to Zebra hardware or simulator.

        Raises:
            aioserial.SerialException: If connection fails (hardware mode)
        """
        if self._connected:
            logger.warning(f"Already connected to {self.port}")
            return

        if self._is_simulation:
            # Import simulator locally to avoid dependency
            from .simulator import ZebraSimulator

            logger.info(f"Starting Zebra simulator for {self.port}")
            self._simulator = ZebraSimulator()
            self._sim_rx_queue = asyncio.Queue()
            self._sim_tx_queue = asyncio.Queue()

            # Set callback for simulator to send interrupt messages
            def send_interrupt(message: str):
                if self._sim_rx_queue:
                    self._sim_rx_queue.put_nowait(message)

            self._simulator.set_send_callback(send_interrupt)

            self._connected = True
            logger.info(f"Simulator ready for {self.port}")

        else:
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
        """Close serial connection or stop simulator."""
        if not self._connected:
            return

        logger.info(f"Disconnecting from {self.port}")

        if self._is_simulation:
            if self._simulator:
                self._simulator.reset()
                self._simulator = None
            self._sim_rx_queue = None
            self._sim_tx_queue = None
        else:
            if self._serial:
                self._serial.close()
                self._serial = None

        self._connected = False
        logger.info("Disconnected from Zebra")

    @property
    def connected(self) -> bool:
        """Check if transport is connected."""
        if self._is_simulation:
            return self._connected and self._simulator is not None
        else:
            return self._connected and self._serial is not None

    async def write_line(self, data: str) -> None:
        """Write a line of text to the Zebra or simulator.

        Automatically appends newline terminator.

        Args:
            data: ASCII text command (without newline)

        Raises:
            RuntimeError: If not connected
        """
        if not self.connected:
            raise RuntimeError("Not connected to Zebra")

        logger.debug(f"TX: {data!r}")

        if self._is_simulation:
            # Queue command for simulator processing
            if self._sim_tx_queue:
                await self._sim_tx_queue.put(data)

                # Process command and get response
                if self._simulator:
                    response = await self._simulator.process_command(data)
                    # Queue response for reading
                    if response and self._sim_rx_queue:
                        self._sim_rx_queue.put_nowait(response)
        else:
            line = data + "\n"
            await self._serial.write_async(  # type: ignore[union-attr]
                line.encode("ascii")
            )

    async def read_line(self, timeout: float | None = None) -> str:
        """Read a line of text from the Zebra or simulator.

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
            if self._is_simulation:
                # Read from simulator response queue
                if not self._sim_rx_queue:
                    raise RuntimeError("Simulator not properly initialized")

                line = await asyncio.wait_for(self._sim_rx_queue.get(), timeout=timeout)
            else:
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
