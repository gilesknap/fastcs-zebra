import subprocess
import sys

from fastcs_zebra import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "fastcs_zebra", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
