"""FastCS Zebra EPICS server entry point.

Launches a FastCS server that exposes Zebra hardware control via EPICS PVs.

Usage:
    python -m fastcs_zebra --port /dev/ttyUSB0 --pv-prefix BL99I-EA-ZEBRA-01:
"""

import logging
from argparse import ArgumentParser
from collections.abc import Sequence

from . import __version__
from .zebra_controller import ZebraController

__all__ = ["main"]


def main(args: Sequence[str] | None = None) -> None:
    """Launch the FastCS Zebra EPICS server."""
    parser = ArgumentParser(description="FastCS Zebra EPICS Server")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "--port",
        type=str,
        required=True,
        help="Serial port path (e.g., /dev/ttyUSB0, COM3)",
    )
    parser.add_argument(
        "--pv-prefix",
        type=str,
        default="ZEBRA:",
        help="EPICS PV prefix (default: ZEBRA:)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    parsed_args = parser.parse_args(args)

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, parsed_args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Import FastCS components (optional dependency for EPICS)
    try:
        from fastcs.launch import FastCS
        from fastcs.transports.epics.ca import EpicsCATransport
        from fastcs.transports.epics.options import EpicsIOCOptions
    except ImportError as e:
        print(f"Error: FastCS EPICS transport not available: {e}")
        print("Please install with: pip install 'fastcs[ca]'")
        return

    # Create controller
    controller = ZebraController(port=parsed_args.port)

    # Create EPICS transport
    transport = EpicsCATransport(
        epicsca=EpicsIOCOptions(pv_prefix=parsed_args.pv_prefix)
    )

    # Launch FastCS
    fastcs = FastCS(controller, [transport])
    fastcs.run()


if __name__ == "__main__":
    main()
