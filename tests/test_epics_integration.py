"""Pytest tests for EPICS integration.

These tests verify that the FastCS EPICS interface is working correctly.
They require a running EPICS IOC (python -m fastcs_zebra).

Run with: pytest tests/test_epics_integration.py -v
"""

import time

import pytest

# Import EPICS clients
try:
    from epicscorelibs.ca import cadef  # Channel Access
except ImportError:
    cadef = None

try:
    from p4p.client.thread import Context  # PVAccess
except ImportError:
    Context = None


# PV prefix can be overridden with pytest --prefix option
PV_PREFIX = "ZEBRA:"


def pytest_addoption(parser):
    """Add command line option for PV prefix."""
    parser.addoption(
        "--prefix",
        action="store",
        default="ZEBRA:",
        help="EPICS PV prefix (default: ZEBRA:)",
    )


@pytest.fixture(scope="module")
def pv_prefix(request):
    """Get the PV prefix from command line or use default."""
    return request.config.getoption("--prefix")


# Channel Access tests using epicscorelibs


@pytest.fixture(scope="module")
def ca_context():
    """Initialize Channel Access context."""
    if cadef is None:
        pytest.skip("epicscorelibs not available")
    cadef.ca_context_create()
    yield
    cadef.ca_context_destroy()


def ca_get(pv_name: str, timeout: float = 5.0):
    """Get a PV value using Channel Access."""
    chid = cadef.ca_create_channel(pv_name.encode())
    cadef.ca_pend_io(timeout)
    value = cadef.ca_get(chid)
    cadef.ca_pend_io(timeout)
    cadef.ca_clear_channel(chid)
    return value


def ca_put(pv_name: str, value, timeout: float = 5.0):
    """Put a PV value using Channel Access."""
    chid = cadef.ca_create_channel(pv_name.encode())
    cadef.ca_pend_io(timeout)
    cadef.ca_put(chid, value)
    cadef.ca_pend_io(timeout)
    cadef.ca_clear_channel(chid)


@pytest.mark.parametrize(
    "pv_name",
    ["CONNECTED", "SYS_VER", "SYS_STATERR", "PC_NUM_CAP"],
)
def test_ca_read_only_pvs(ca_context, pv_prefix, pv_name):
    """Test that read-only PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = ca_get(full_pv)
    assert value is not None


@pytest.mark.parametrize(
    "pv_name",
    ["PC_ENC", "PC_TSPRE", "SOFT_IN"],
)
def test_ca_read_write_pvs(ca_context, pv_prefix, pv_name):
    """Test that read-write PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = ca_get(full_pv)
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
def test_ca_last_captured_pvs(ca_context, pv_prefix, pv_name):
    """Test that last captured value PVs can be read via Channel Access."""
    full_pv = f"{pv_prefix}{pv_name}"
    value = ca_get(full_pv)
    assert value is not None


def test_ca_status_message(ca_context, pv_prefix):
    """Test that status message PV can be read via Channel Access."""
    full_pv = f"{pv_prefix}STATUS_MSG"
    value = ca_get(full_pv)
    assert value is not None


def test_ca_soft_in_write(ca_context, pv_prefix):
    """Test writing to SOFT_IN via Channel Access."""
    full_pv = f"{pv_prefix}SOFT_IN"
    # Write a value
    ca_put(full_pv, 5)
    time.sleep(0.5)
    # Read it back
    value = ca_get(full_pv)
    assert value == 5


def test_ca_pc_enc_write(ca_context, pv_prefix):
    """Test writing to PC_ENC via Channel Access."""
    full_pv = f"{pv_prefix}PC_ENC"
    # Write a value
    ca_put(full_pv, 0)
    time.sleep(0.5)
    # Read it back
    value = ca_get(full_pv)
    assert value == 0


# PVAccess tests using p4p


@pytest.fixture(scope="module")
def pva_context():
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
