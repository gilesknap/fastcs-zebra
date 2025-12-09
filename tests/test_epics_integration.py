"""Pytest tests for EPICS integration.

These tests verify that the FastCS EPICS interface is working correctly.
The IOC is automatically started for the tests.

For testing without hardware, you need to:
1. Create a virtual serial port pair with socat, OR
2. Have a Zebra hardware simulator running

Run with: uv run pytest tests/test_epics_integration.py -v --port /dev/ttyUSB0
Or with virtual ports:
    uv run pytest tests/test_epics_integration.py -v --port /tmp/vserial0
"""

import subprocess
import time

import pytest

# Import EPICS clients
from cothread.catools import caget, caput  # Channel Access with cothread

try:
    from p4p.client.thread import Context  # PVAccess
except ImportError:
    Context = None


@pytest.fixture(scope="module")
def pv_prefix(request):
    """Get the PV prefix from command line or use default."""
    return request.config.getoption("--prefix")


@pytest.fixture(scope="module")
def zebra_port(request):
    """Get the Zebra serial port from command line or use simulator."""
    port = request.config.getoption("--port", default=None)
    if port is None:
        # Default to simulator if no port specified
        return "sim://zebra"
    return port


@pytest.fixture(scope="module")
def zebra_ioc(pv_prefix, zebra_port):
    """Start the FastCS Zebra IOC for testing."""
    if caget is None:
        pytest.skip("cothread not available")

    # Start the IOC using uv run to ensure correct environment
    # Don't capture stdout/stderr to allow interactive shell to run
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "-m",
            "fastcs_zebra",
            "--port",
            zebra_port,
            "--pv-prefix",
            pv_prefix,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for IOC to be ready (try connecting to a PV)
    max_wait = 10
    connected = False
    for _ in range(max_wait * 10):
        try:
            caget(f"{pv_prefix}CONNECTED", timeout=0.1)
            connected = True
            break
        except Exception:
            time.sleep(0.1)

    if not connected:
        proc.terminate()
        proc.wait(timeout=5)
        pytest.skip(f"IOC failed to start on port {zebra_port}")

    yield proc

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


# Channel Access tests using cothread


@pytest.mark.parametrize(
    "pv_name",
    ["CONNECTED", "SYS_VER", "SYS_STATERR", "PC_NUM_CAP"],
)
def test_ca_read_only_pvs(zebra_ioc, pv_prefix, pv_name):
    """Test that read-only PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = caget(full_pv, timeout=5.0)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    ["PC_ENC", "PC_TSPRE", "SOFT_IN"],
)
def test_ca_read_write_pvs(zebra_ioc, pv_prefix, pv_name):
    """Test that read-write PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = caget(full_pv, timeout=5.0)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    [
        "PC_TIME_LAST",
        "PC_ENC1_LAST",
        "PC_ENC2_LAST",
        "PC_ENC3_LAST",
        "PC_ENC4_LAST",
    ],
)
def test_ca_last_captured_pvs(zebra_ioc, pv_prefix, pv_name):
    """Test that last captured value PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = caget(full_pv, timeout=5.0)
    assert value is not None


def test_ca_status_message(zebra_ioc, pv_prefix):
    """Test that status message PV can be read via Channel Access."""
    full_pv = f"{pv_prefix}STATUS_MSG"
    value = caget(full_pv, timeout=5.0)
    assert value is not None


def test_ca_soft_in_write(zebra_ioc, pv_prefix):
    """Test writing to SOFT_IN via Channel Access."""
    full_pv = f"{pv_prefix}SOFT_IN"
    # Write a value
    caput(full_pv, 5, wait=True, timeout=5.0)
    time.sleep(0.5)
    # Read it back
    value = caget(full_pv, timeout=5.0)
    assert value == 5


def test_ca_pc_enc_write(zebra_ioc, pv_prefix):
    """Test writing to PC_ENC via Channel Access."""
    full_pv = f"{pv_prefix}PC_ENC"
    # Write a value
    caput(full_pv, 0, wait=True, timeout=5.0)
    time.sleep(0.5)
    # Read it back
    value = caget(full_pv, timeout=5.0)
    assert value == 0


# PVAccess tests using p4p


@pytest.fixture(scope="module")
def pva_context(zebra_ioc):
    """Initialize PVAccess context."""
    if Context is None:
        pytest.skip("p4p not available")
    ctx = Context("pva")
    yield ctx
    ctx.close()


@pytest.mark.parametrize(
    "pv_name",
    ["CONNECTED", "SYS_VER", "SYS_STATERR", "PC_NUM_CAP"],
)
def test_pva_read_only_pvs(pva_context, pv_prefix, pv_name):
    """Test that read-only PVs can be read via PVAccess."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = pva_context.get(full_pv, timeout=5.0)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    ["PC_ENC", "PC_TSPRE", "SOFT_IN"],
)
def test_pva_read_write_pvs(pva_context, pv_prefix, pv_name):
    """Test that read-write PVs can be read via PVAccess."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = pva_context.get(full_pv, timeout=5.0)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    [
        "PC_TIME_LAST",
        "PC_ENC1_LAST",
        "PC_ENC2_LAST",
        "PC_ENC3_LAST",
        "PC_ENC4_LAST",
    ],
)
def test_pva_last_captured_pvs(pva_context, pv_prefix, pv_name):
    """Test that last captured value PVs can be read via PVAccess."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = pva_context.get(full_pv, timeout=5.0)
    assert value is not None


def test_pva_status_message(pva_context, pv_prefix):
    """Test that status message PV can be read via PVAccess."""
    full_pv = f"{pv_prefix}STATUS_MSG"
    value = pva_context.get(full_pv, timeout=5.0)
    assert value is not None


def test_pva_soft_in_write(pva_context, pv_prefix):
    """Test writing to SOFT_IN via PVAccess."""
    full_pv = f"{pv_prefix}SOFT_IN"
    # Write a value
    pva_context.put(full_pv, 5, timeout=5.0)
    time.sleep(0.5)
    # Read it back
    value = pva_context.get(full_pv, timeout=5.0)
    assert value == 5


def test_pva_pc_enc_write(pva_context, pv_prefix):
    """Test writing to PC_ENC via PVAccess."""
    full_pv = f"{pv_prefix}PC_ENC"
    # Write a value
    pva_context.put(full_pv, 0, timeout=5.0)
    time.sleep(0.5)
    # Read it back
    value = pva_context.get(full_pv, timeout=5.0)
    assert value == 0
