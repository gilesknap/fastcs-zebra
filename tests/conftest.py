"""Pytest configuration for fastcs-zebra tests."""

import pytest


def pytest_addoption(parser):
    """Add command line options for testing."""
    parser.addoption(
        "--prefix",
        action="store",
        default="ZEBRA",
        help="EPICS PV prefix (default: ZEBRA:)",
    )
    parser.addoption(
        "--port",
        action="store",
        default=None,
        help="Zebra serial port (e.g., /dev/ttyUSB0 or /tmp/vserial0)",
    )
