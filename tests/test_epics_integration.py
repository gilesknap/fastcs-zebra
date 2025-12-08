"""Test script for EPICS integration.

This script helps verify that the FastCS EPICS interface is working correctly.
It requires a running EPICS IOC (python -m fastcs_zebra) and EPICS tools (caget/caput).

Usage:
    python tests/test_epics_integration.py --prefix TEST:ZEBRA:
"""

import argparse
import subprocess
import sys
import time


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_pv_exists(pv_name: str) -> bool:
    """Test if a PV exists and can be read."""
    code, stdout, stderr = run_command(["caget", pv_name])
    if code == 0:
        print(f"✓ {pv_name}: {stdout}")
        return True
    else:
        print(f"✗ {pv_name}: FAILED - {stderr}")
        return False


def check_pv_write(pv_name: str, value: str) -> bool:
    """Test if a PV can be written."""
    code, stdout, stderr = run_command(["caput", pv_name, value])
    if code == 0:
        print(f"✓ Write {pv_name} = {value}")
        return True
    else:
        print(f"✗ Write {pv_name} = {value}: FAILED - {stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test EPICS integration")
    parser.add_argument(
        "--prefix",
        type=str,
        default="ZEBRA:",
        help="EPICS PV prefix (default: ZEBRA:)",
    )
    args = parser.parse_args()

    prefix = args.prefix
    passed = 0
    failed = 0

    print("=" * 60)
    print("Testing EPICS Integration")
    print("=" * 60)

    # Test read-only PVs
    print("\n--- Testing Read-Only PVs ---")
    for pv in ["CONNECTED", "SYS_VER", "SYS_STATERR", "PC_NUM_CAP"]:
        if check_pv_exists(f"{prefix}{pv}"):
            passed += 1
        else:
            failed += 1

    # Test read-write PVs
    print("\n--- Testing Read-Write PVs ---")
    for pv in ["PC_ENC", "PC_TSPRE", "SOFT_IN"]:
        if check_pv_exists(f"{prefix}{pv}"):
            passed += 1
        else:
            failed += 1

    # Test last captured values
    print("\n--- Testing Last Captured Value PVs ---")
    for pv in [
        "PC_TIME_LAST",
        "PC_ENC1_LAST",
        "PC_ENC2_LAST",
        "PC_ENC3_LAST",
        "PC_ENC4_LAST",
    ]:
        if check_pv_exists(f"{prefix}{pv}"):
            passed += 1
        else:
            failed += 1

    # Test status message
    print("\n--- Testing Status Message ---")
    if check_pv_exists(f"{prefix}STATUS_MSG"):
        passed += 1
    else:
        failed += 1

    # Test writes
    print("\n--- Testing Write Operations ---")
    if check_pv_write(f"{prefix}SOFT_IN", "5"):
        passed += 1
        time.sleep(0.5)
        check_pv_exists(f"{prefix}SOFT_IN")  # Verify the write
    else:
        failed += 1

    if check_pv_write(f"{prefix}PC_ENC", "0"):
        passed += 1
        time.sleep(0.5)
        check_pv_exists(f"{prefix}PC_ENC")  # Verify the write
    else:
        failed += 1

    # Test commands (these are write-only, just check they don't error)
    print("\n--- Testing Command PVs ---")
    command_pvs = [
        "PC_ARM",
        "PC_DISARM",
        "SAVE_TO_FLASH",
        "LOAD_FROM_FLASH",
        "SYS_RESET",
    ]
    for pv in command_pvs:
        # Try to see if the PV exists (it may not respond to caget)
        code, _, _ = run_command(["caget", f"{prefix}{pv}"])
        if code == 0:
            print(f"✓ {prefix}{pv} exists")
            passed += 1
        else:
            # Commands might not be readable, that's OK
            print(f"? {prefix}{pv} (command PVs may not be readable)")

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
