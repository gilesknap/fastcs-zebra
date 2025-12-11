"""Pytest tests for EPICS integration.

These tests verify that the FastCS EPICS interface is working correctly.
The IOC is automatically started for the tests.

For testing without hardware, you need to:
1. Create a virtual serial port pair with socat, OR
2. Have a Zebra hardware simulator running

Run with: uv run pytest tests/test_epics_integration.py -v --port /dev/ttyUSB0
Or with virtual ports:
    uv run pytest tests/test_epics_integration.py -v
"""

import subprocess
import sys
import time

import pytest

# Import EPICS clients
from cothread.catools import caget, caput  # Channel Access with cothread
from p4p.client.thread import Context  # PVAccess


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

    # Start the IOC using the same Python interpreter running the tests
    # This ensures we use the correct environment in CI
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "fastcs_zebra",
            "--port",
            zebra_port,
            "--pv-prefix",
            pv_prefix,
            "--no-interactive",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for IOC to be ready (try connecting to a PV)
    # Increase timeout for CI environments
    max_wait = 5
    connected = False
    for _ in range(max_wait * 10):
        try:
            caget(f"{pv_prefix}:Connected", timeout=0.1)
            connected = True
            break
        except Exception:
            time.sleep(0.1)

    if not connected:
        # Capture output for debugging
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=1.0)
            error_msg = f"IOC failed to start on port {zebra_port}\n"
            if stderr:
                error_msg += f"STDERR:\n{stderr.decode()}\n"
            if stdout:
                error_msg += f"STDOUT:\n{stdout.decode()}\n"
            pytest.fail(error_msg)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            pytest.fail(f"IOC failed to start on port {zebra_port}")

    yield proc

    # Cleanup
    proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=1.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()


# Channel Access tests using cothread


@pytest.mark.parametrize(
    "pv_name",
    ["Connected", "SysVer", "SysStaterr", "PcNumCap"],
)
def test_ca_read_only_pvs(zebra_ioc, pv_prefix, pv_name):
    """Test that read-only PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}:{pv_name}"
    value = caget(full_pv, timeout=0.1)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    ["PcEnc", "PcTspre", "SoftIn"],
)
def test_ca_read_write_pvs(zebra_ioc, pv_prefix, pv_name):
    """Test that read-write PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}:{pv_name}"
    value = caget(full_pv, timeout=0.1)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    [
        "PcTimeLast",
        "PcEnc1Last",
        "PcEnc2Last",
        "PcEnc3Last",
        "PcEnc4Last",
    ],
)
def test_ca_last_captured_pvs(zebra_ioc, pv_prefix, pv_name):
    """Test that last captured value PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}:{pv_name}"
    value = caget(full_pv, timeout=0.1)
    assert value is not None


def test_ca_status_message(zebra_ioc, pv_prefix):
    """Test that status message PV can be read via Channel Access."""
    full_pv = f"{pv_prefix}:StatusMsg"
    value = caget(full_pv, timeout=0.1)
    assert value is not None


def test_ca_soft_in_write(zebra_ioc, pv_prefix):
    """Test writing to SOFT_IN via Channel Access."""
    full_pv = f"{pv_prefix}:SoftIn"
    # Write a value
    caput(full_pv, 5, wait=True, timeout=0.1)
    time.sleep(0.5)
    # Read it back
    value = caget(full_pv, timeout=0.1)
    assert value == 5


def test_ca_pc_enc_write(zebra_ioc, pv_prefix):
    """Test writing to PC_ENC via Channel Access."""
    full_pv = f"{pv_prefix}:PcEnc"
    # Write a value
    caput(full_pv, 0, wait=True, timeout=0.1)
    time.sleep(0.5)
    # Read it back
    value = caget(full_pv, timeout=0.1)
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
    ["Connected", "SysVer", "SysStaterr", "PcNumCap"],
)
def test_pva_read_only_pvs(pva_context, pv_prefix, pv_name):
    """Test that read-only PVs can be read via PVAccess."""
    full_pv = f"{pv_prefix}:{pv_name}"
    value = pva_context.get(full_pv, timeout=0.1)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    ["PcEnc", "PcTspre", "SoftIn"],
)
def test_pva_read_write_pvs(pva_context, pv_prefix, pv_name):
    """Test that read-write PVs can be read via PVAccess."""
    full_pv = f"{pv_prefix}:{pv_name}"
    value = pva_context.get(full_pv, timeout=0.1)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    [
        "PcTimeLast",
        "PcEnc1Last",
        "PcEnc2Last",
        "PcEnc3Last",
        "PcEnc4Last",
    ],
)
def test_pva_last_captured_pvs(pva_context, pv_prefix, pv_name):
    """Test that last captured value PVs can be read via PVAccess."""
    full_pv = f"{pv_prefix}:{pv_name}"
    value = pva_context.get(full_pv, timeout=0.1)
    assert value is not None


def test_pva_status_message(pva_context, pv_prefix):
    """Test that status message PV can be read via PVAccess."""
    full_pv = f"{pv_prefix}:StatusMsg"
    value = pva_context.get(full_pv, timeout=0.1)
    assert value is not None


def test_pva_soft_in_write(pva_context, pv_prefix):
    """Test writing to SOFT_IN via PVAccess."""
    full_pv = f"{pv_prefix}:SoftIn"
    # Write a value
    pva_context.put(full_pv, 5, timeout=0.1)
    time.sleep(0.5)
    # Read it back
    value = pva_context.get(full_pv, timeout=0.1)
    assert value == 5


def test_pva_pc_enc_write(pva_context, pv_prefix):
    """Test writing to PC_ENC via PVAccess."""
    full_pv = f"{pv_prefix}:PcEnc"
    # Write a value
    pva_context.put(full_pv, 0, timeout=0.1)
    time.sleep(0.5)
    # Read it back
    value = pva_context.get(full_pv, timeout=0.1)
    assert value == 0
