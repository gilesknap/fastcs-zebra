"""Unit tests for ZebraController.

These tests directly call the controller methods without using EPICS.
They can use either real hardware or a simulator.

Run with: uv run pytest tests/test_controller.py -v --port /dev/ttyUSB0
Or with simulator (default):
    uv run pytest tests/test_controller.py -v
"""

import asyncio

import pytest

from fastcs_zebra.zebra_controller import ZebraController


@pytest.fixture
async def zebra_port(request):
    """Get the Zebra serial port from command line or use simulator."""
    port = request.config.getoption("--port", default=None)
    if port is None:
        # Default to simulator if no port specified
        return "sim://zebra"
    return port


@pytest.fixture
async def zebra_controller(zebra_port):
    """Create and connect a ZebraController instance for testing."""
    controller = ZebraController(zebra_port)
    # Must call post_initialise before connect to set up IO callbacks
    controller.post_initialise()
    await controller.connect()
    yield controller
    await controller.disconnect()


# Read-only attribute tests


@pytest.mark.asyncio
async def test_connected_attribute(zebra_controller):
    """Test that connected attribute is True after connection."""
    value = zebra_controller.connected.get()
    assert value is True


@pytest.mark.asyncio
async def test_sys_ver_attribute(zebra_controller):
    """Test reading firmware version."""
    value = zebra_controller.sys_ver.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_sys_staterr_attribute(zebra_controller):
    """Test reading system state/error register."""
    value = zebra_controller.sys_staterr.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_pc_num_cap_attribute(zebra_controller):
    """Test reading number of position compare captures (32-bit)."""
    value = zebra_controller.pc_num_cap.get()
    assert value is not None
    assert isinstance(value, int)


# Read-write attribute tests


@pytest.mark.asyncio
async def test_pc_enc_read(zebra_controller):
    """Test reading position compare encoder selection."""
    value = zebra_controller.pc_enc.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_pc_tspre_read(zebra_controller):
    """Test reading timestamp prescaler."""
    value = zebra_controller.pc_tspre.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_soft_in_read(zebra_controller):
    """Test reading soft inputs."""
    value = zebra_controller.soft_in.get()
    assert value is not None
    assert isinstance(value, int)


# Attribute write tests


@pytest.mark.asyncio
async def test_soft_in_write(zebra_controller):
    """Test writing to SOFT_IN register."""
    # Write a value
    await zebra_controller.soft_in.put(5)
    # Read it back
    value = zebra_controller.soft_in.get()
    assert value == 5


@pytest.mark.asyncio
async def test_pc_enc_write(zebra_controller):
    """Test writing to PC_ENC register."""
    # Write a value
    await zebra_controller.pc_enc.put(0)
    # Read it back
    value = zebra_controller.pc_enc.get()
    assert value == 0


@pytest.mark.asyncio
async def test_pc_tspre_write(zebra_controller):
    """Test writing to PC_TSPRE register."""
    # Write a value (5 = milliseconds prescaler)
    await zebra_controller.pc_tspre.put(5)
    # Read it back
    value = zebra_controller.pc_tspre.get()
    assert value == 5


# Last captured value tests (interrupt-driven)


@pytest.mark.asyncio
async def test_pc_time_last_attribute(zebra_controller):
    """Test reading last captured timestamp."""
    value = zebra_controller.pc_time_last.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_pc_enc1_last_attribute(zebra_controller):
    """Test reading last captured encoder 1 value."""
    value = zebra_controller.pc_enc1_last.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_pc_enc2_last_attribute(zebra_controller):
    """Test reading last captured encoder 2 value."""
    value = zebra_controller.pc_enc2_last.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_pc_enc3_last_attribute(zebra_controller):
    """Test reading last captured encoder 3 value."""
    value = zebra_controller.pc_enc3_last.get()
    assert value is not None
    assert isinstance(value, int)


@pytest.mark.asyncio
async def test_pc_enc4_last_attribute(zebra_controller):
    """Test reading last captured encoder 4 value."""
    value = zebra_controller.pc_enc4_last.get()
    assert value is not None
    assert isinstance(value, int)


# Status message test


@pytest.mark.asyncio
async def test_status_msg_attribute(zebra_controller):
    """Test reading status message."""
    value = zebra_controller.status_msg.get()
    assert value is not None
    assert isinstance(value, str)
    # Should contain connection info after connect
    assert len(value) > 0


# Command tests


@pytest.mark.asyncio
async def test_pc_arm_disarm_command(zebra_controller):
    """Test position compare arm command."""
    # Should not raise an exception
    await zebra_controller.pc_arm()
    # Check status message was updated
    status = zebra_controller.status_msg.get()
    assert "Armed" in status or "arm" in status.lower()
    # Give it a moment to process the arm and generate at least one interrupt
    await asyncio.sleep(0.2)
    # Clean up: disarm after test
    await zebra_controller.pc_disarm()
    # Give it a moment to process the disarm
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_save_to_flash_command(zebra_controller):
    """Test save to flash command."""
    # Should not raise an exception
    await zebra_controller.save_to_flash()
    # Check status message was updated
    status = zebra_controller.status_msg.get()
    assert "flash" in status.lower() or "Saved" in status


@pytest.mark.asyncio
async def test_load_from_flash_command(zebra_controller):
    """Test load from flash command."""
    # Should not raise an exception
    await zebra_controller.load_from_flash()
    # Check status message was updated
    status = zebra_controller.status_msg.get()
    assert "flash" in status.lower() or "Loaded" in status


@pytest.mark.asyncio
async def test_sys_reset_command(zebra_controller):
    """Test system reset command."""
    # Should not raise an exception
    await zebra_controller.sys_reset()
    # Check status message was updated
    status = zebra_controller.status_msg.get()
    assert "reset" in status.lower() or "Reset" in status
