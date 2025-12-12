"""Unit tests for Zebra sub-controllers.

Tests for the Phase 3 controller hierarchy:
- AND gates (AND1-4)
- OR gates (OR1-4)
- Gate generators (GATE1-4)
- Pulse generators (PULSE1-4)
- Pulse dividers (DIV1-4)
- Output routing (OUT1-8)
- Position compare subsystem
"""

import pytest

from fastcs_zebra.zebra_controller import ZebraController


@pytest.fixture
async def zebra_port(request):
    """Get the Zebra serial port from command line or use simulator."""
    port = request.config.getoption("--port", default=None)
    if port is None:
        return "sim://zebra"
    return port


@pytest.fixture
async def zebra_controller(zebra_port):
    """Create and connect a ZebraController instance for testing."""
    controller = ZebraController(zebra_port)
    controller.post_initialise()
    await controller.connect()
    yield controller
    await controller.disconnect()


# =============================================================================
# Sub-controller Structure Tests
# =============================================================================


class TestControllerHierarchy:
    """Test that sub-controllers are properly created."""

    @pytest.mark.asyncio
    async def test_and_gates_exist(self, zebra_controller):
        """Test that AND gate sub-controllers exist."""
        for i in range(1, 5):
            controller = getattr(zebra_controller, f"and{i}")
            assert controller is not None

    @pytest.mark.asyncio
    async def test_or_gates_exist(self, zebra_controller):
        """Test that OR gate sub-controllers exist."""
        for i in range(1, 5):
            controller = getattr(zebra_controller, f"or{i}")
            assert controller is not None

    @pytest.mark.asyncio
    async def test_gate_generators_exist(self, zebra_controller):
        """Test that gate generator sub-controllers exist."""
        for i in range(1, 5):
            controller = getattr(zebra_controller, f"gate{i}")
            assert controller is not None

    @pytest.mark.asyncio
    async def test_pulse_generators_exist(self, zebra_controller):
        """Test that pulse generator sub-controllers exist."""
        for i in range(1, 5):
            controller = getattr(zebra_controller, f"pulse{i}")
            assert controller is not None

    @pytest.mark.asyncio
    async def test_dividers_exist(self, zebra_controller):
        """Test that divider sub-controllers exist."""
        for i in range(1, 5):
            controller = getattr(zebra_controller, f"div{i}")
            assert controller is not None

    @pytest.mark.asyncio
    async def test_outputs_exist(self, zebra_controller):
        """Test that output sub-controllers exist."""
        for i in range(1, 9):
            controller = getattr(zebra_controller, f"out{i}")
            assert controller is not None

    @pytest.mark.asyncio
    async def test_position_compare_exists(self, zebra_controller):
        """Test that position compare sub-controller exists."""
        assert zebra_controller.pc is not None


# =============================================================================
# AND Gate Tests
# =============================================================================


class TestAndGates:
    """Tests for AND gate sub-controllers."""

    @pytest.mark.asyncio
    async def test_and1_attributes_exist(self, zebra_controller):
        """Test that AND1 has all required attributes."""
        and1 = zebra_controller.and1
        assert hasattr(and1, "inv")
        assert hasattr(and1, "ena")
        assert hasattr(and1, "inp1")
        assert hasattr(and1, "inp2")
        assert hasattr(and1, "inp3")
        assert hasattr(and1, "inp4")
        assert hasattr(and1, "out")

    @pytest.mark.asyncio
    async def test_and1_read_inputs(self, zebra_controller):
        """Test reading AND1 input values."""
        and1 = zebra_controller.and1
        # These should return integers (system bus indices)
        for i in range(1, 5):
            value = getattr(and1, f"inp{i}").get()
            assert value is not None
            assert isinstance(value, int)

    @pytest.mark.asyncio
    async def test_and1_write_input(self, zebra_controller):
        """Test writing to AND1 input."""
        and1 = zebra_controller.and1
        # Write a value (DISCONNECT = 0)
        await and1.inp1.put(0)
        value = and1.inp1.get()
        assert value == 0


# =============================================================================
# OR Gate Tests
# =============================================================================


class TestOrGates:
    """Tests for OR gate sub-controllers."""

    @pytest.mark.asyncio
    async def test_or1_attributes_exist(self, zebra_controller):
        """Test that OR1 has all required attributes."""
        or1 = zebra_controller.or1
        assert hasattr(or1, "inv")
        assert hasattr(or1, "ena")
        assert hasattr(or1, "inp1")
        assert hasattr(or1, "inp2")
        assert hasattr(or1, "inp3")
        assert hasattr(or1, "inp4")
        assert hasattr(or1, "out")

    @pytest.mark.asyncio
    async def test_or1_read_inputs(self, zebra_controller):
        """Test reading OR1 input values."""
        or1 = zebra_controller.or1
        for i in range(1, 5):
            value = getattr(or1, f"inp{i}").get()
            assert value is not None
            assert isinstance(value, int)


# =============================================================================
# Gate Generator Tests
# =============================================================================


class TestGateGenerators:
    """Tests for gate generator sub-controllers."""

    @pytest.mark.asyncio
    async def test_gate1_attributes_exist(self, zebra_controller):
        """Test that GATE1 has all required attributes."""
        gate1 = zebra_controller.gate1
        assert hasattr(gate1, "inp1")
        assert hasattr(gate1, "inp2")
        assert hasattr(gate1, "out")

    @pytest.mark.asyncio
    async def test_gate1_read_inputs(self, zebra_controller):
        """Test reading GATE1 input values."""
        gate1 = zebra_controller.gate1
        value1 = gate1.inp1.get()
        value2 = gate1.inp2.get()
        assert value1 is not None
        assert value2 is not None


# =============================================================================
# Pulse Generator Tests
# =============================================================================


class TestPulseGenerators:
    """Tests for pulse generator sub-controllers."""

    @pytest.mark.asyncio
    async def test_pulse1_attributes_exist(self, zebra_controller):
        """Test that PULSE1 has all required attributes."""
        pulse1 = zebra_controller.pulse1
        assert hasattr(pulse1, "inp")
        assert hasattr(pulse1, "dly")
        assert hasattr(pulse1, "wid")
        assert hasattr(pulse1, "pre")
        assert hasattr(pulse1, "out")

    @pytest.mark.asyncio
    async def test_pulse1_read_values(self, zebra_controller):
        """Test reading PULSE1 values."""
        pulse1 = zebra_controller.pulse1
        dly = pulse1.dly.get()
        wid = pulse1.wid.get()
        pre = pulse1.pre.get()
        assert dly is not None
        assert wid is not None
        assert pre is not None

    @pytest.mark.asyncio
    async def test_pulse1_write_delay(self, zebra_controller):
        """Test writing to PULSE1 delay."""
        pulse1 = zebra_controller.pulse1
        await pulse1.dly.put(100)
        value = pulse1.dly.get()
        assert value == 100


# =============================================================================
# Divider Tests
# =============================================================================


class TestDividers:
    """Tests for divider sub-controllers."""

    @pytest.mark.asyncio
    async def test_div1_attributes_exist(self, zebra_controller):
        """Test that DIV1 has all required attributes."""
        div1 = zebra_controller.div1
        assert hasattr(div1, "inp")
        assert hasattr(div1, "div")
        assert hasattr(div1, "outd")
        assert hasattr(div1, "outn")

    @pytest.mark.asyncio
    async def test_div1_read_divisor(self, zebra_controller):
        """Test reading DIV1 divisor (32-bit value)."""
        div1 = zebra_controller.div1
        value = div1.div.get()
        assert value is not None
        assert isinstance(value, int)

    @pytest.mark.asyncio
    async def test_div1_write_divisor(self, zebra_controller):
        """Test writing to DIV1 divisor."""
        div1 = zebra_controller.div1
        await div1.div.put(1000)
        value = div1.div.get()
        assert value == 1000


# =============================================================================
# Output Tests
# =============================================================================


class TestOutputs:
    """Tests for output routing sub-controllers."""

    @pytest.mark.asyncio
    async def test_out1_attributes_exist(self, zebra_controller):
        """Test that OUT1 has TTL, NIM, LVDS attributes."""
        out1 = zebra_controller.out1
        assert hasattr(out1, "ttl")
        assert hasattr(out1, "nim")
        assert hasattr(out1, "lvds")

    @pytest.mark.asyncio
    async def test_out3_has_oc(self, zebra_controller):
        """Test that OUT3 has open collector output."""
        out3 = zebra_controller.out3
        assert hasattr(out3, "ttl")
        assert hasattr(out3, "oc")
        assert hasattr(out3, "lvds")

    @pytest.mark.asyncio
    async def test_out4_has_pecl(self, zebra_controller):
        """Test that OUT4 has PECL output."""
        out4 = zebra_controller.out4
        assert hasattr(out4, "ttl")
        assert hasattr(out4, "nim")
        assert hasattr(out4, "pecl")

    @pytest.mark.asyncio
    async def test_out5_encoder_outputs(self, zebra_controller):
        """Test that OUT5 has encoder outputs."""
        out5 = zebra_controller.out5
        assert hasattr(out5, "enca")
        assert hasattr(out5, "encb")
        assert hasattr(out5, "encz")
        assert hasattr(out5, "conn")

    @pytest.mark.asyncio
    async def test_out1_read_ttl(self, zebra_controller):
        """Test reading OUT1 TTL value."""
        out1 = zebra_controller.out1
        value = out1.ttl.get()
        assert value is not None
        assert isinstance(value, int)


# =============================================================================
# Position Compare Tests
# =============================================================================


class TestPositionCompare:
    """Tests for position compare sub-controller."""

    @pytest.mark.asyncio
    async def test_pc_encoder_attributes_exist(self, zebra_controller):
        """Test that PC has encoder and timing attributes."""
        pc = zebra_controller.pc
        assert hasattr(pc, "enc")
        assert hasattr(pc, "tspre")
        assert hasattr(pc, "dir")

    @pytest.mark.asyncio
    async def test_pc_arm_attributes_exist(self, zebra_controller):
        """Test that PC has arm configuration attributes."""
        pc = zebra_controller.pc
        assert hasattr(pc, "arm_sel")
        assert hasattr(pc, "arm_inp")
        assert hasattr(pc, "arm_out")

    @pytest.mark.asyncio
    async def test_pc_gate_attributes_exist(self, zebra_controller):
        """Test that PC has gate configuration attributes."""
        pc = zebra_controller.pc
        assert hasattr(pc, "gate_sel")
        assert hasattr(pc, "gate_inp")
        assert hasattr(pc, "gate_start")
        assert hasattr(pc, "gate_wid")
        assert hasattr(pc, "gate_ngate")
        assert hasattr(pc, "gate_step")
        assert hasattr(pc, "gate_out")

    @pytest.mark.asyncio
    async def test_pc_pulse_attributes_exist(self, zebra_controller):
        """Test that PC has pulse configuration attributes."""
        pc = zebra_controller.pc
        assert hasattr(pc, "pulse_sel")
        assert hasattr(pc, "pulse_inp")
        assert hasattr(pc, "pulse_start")
        assert hasattr(pc, "pulse_wid")
        assert hasattr(pc, "pulse_step")
        assert hasattr(pc, "pulse_max")
        assert hasattr(pc, "pulse_dly")
        assert hasattr(pc, "pulse_out")

    @pytest.mark.asyncio
    async def test_pc_capture_attributes_exist(self, zebra_controller):
        """Test that PC has capture configuration attributes."""
        pc = zebra_controller.pc
        assert hasattr(pc, "bit_cap")
        assert hasattr(pc, "num_cap")

    @pytest.mark.asyncio
    async def test_pc_last_values_exist(self, zebra_controller):
        """Test that PC has last captured value attributes."""
        pc = zebra_controller.pc
        assert hasattr(pc, "time_last")
        assert hasattr(pc, "enc1_last")
        assert hasattr(pc, "enc2_last")
        assert hasattr(pc, "enc3_last")
        assert hasattr(pc, "enc4_last")

    @pytest.mark.asyncio
    async def test_pc_read_encoder(self, zebra_controller):
        """Test reading PC encoder selection."""
        pc = zebra_controller.pc
        value = pc.enc.get()
        assert value is not None
        assert isinstance(value, int)

    @pytest.mark.asyncio
    async def test_pc_write_gate_start(self, zebra_controller):
        """Test writing to PC gate start (32-bit value)."""
        pc = zebra_controller.pc
        await pc.gate_start.put(1000)
        value = pc.gate_start.get()
        assert value == 1000


# =============================================================================
# System Status Tests
# =============================================================================


class TestSystemStatus:
    """Tests for system bus status attributes."""

    @pytest.mark.asyncio
    async def test_sys_stat1_exists(self, zebra_controller):
        """Test that sys_stat1 attribute exists."""
        assert hasattr(zebra_controller, "sys_stat1")

    @pytest.mark.asyncio
    async def test_sys_stat2_exists(self, zebra_controller):
        """Test that sys_stat2 attribute exists."""
        assert hasattr(zebra_controller, "sys_stat2")

    @pytest.mark.asyncio
    async def test_div_first_exists(self, zebra_controller):
        """Test that div_first attribute exists."""
        assert hasattr(zebra_controller, "div_first")

    @pytest.mark.asyncio
    async def test_polarity_exists(self, zebra_controller):
        """Test that polarity attribute exists."""
        assert hasattr(zebra_controller, "polarity")
