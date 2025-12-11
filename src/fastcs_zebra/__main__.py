"""FastCS Zebra EPICS server entry point.

Launches a FastCS server that exposes Zebra hardware control via EPICS PVs.

Usage:
    python -m fastcs_zebra --port /dev/ttyUSB0 --pv-prefix BL99I-EA-ZEBRA-01:
"""

import logging
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

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
        default="ZEBRA",
        help="EPICS PV prefix (default: ZEBRA)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--gui",
        type=str,
        default=None,
        help="Generate Phoebus screen file (e.g., zebra.bob)",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Run in interactive mode (default: True)",
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
        from fastcs.transports.epics.options import (
            EpicsGUIOptions,
            EpicsIOCOptions,
        )
    except ImportError as e:
        print(f"Error: FastCS EPICS transport not available: {e}")
        print("Please install with: pip install 'fastcs[ca]'")
        return

    # Create controller
    controller = ZebraController(port=parsed_args.port)

    # Setup GUI options if requested
    gui_options = None
    if parsed_args.gui:
        gui_path = Path(parsed_args.gui)
        gui_options = EpicsGUIOptions(
            output_path=gui_path,
            title="Zebra Position Compare Controller",
        )

    # Create EPICS transport
    transport = EpicsCATransport(
        gui=gui_options,
        epicsca=EpicsIOCOptions(pv_prefix=parsed_args.pv_prefix),
    )

    # Launch FastCS (non-interactive for daemon mode)
    fastcs = FastCS(controller, [transport])
    fastcs.run(interactive=not parsed_args.no_interactive)


if __name__ == "__main__":
    main()
