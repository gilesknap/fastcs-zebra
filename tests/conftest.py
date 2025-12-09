"""Pytest configuration for fastcs-zebra tests."""

import pytest


def pytest_addoption(parser):
    """Add command line option for PV prefix."""
    parser.addoption(
        "--prefix",
        action="store",
        default="ZEBRA:",
        help="EPICS PV prefix (default: ZEBRA:)",
    )
