"""Runs the unit tests of the page's logic, which are written for Node's own test runner."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_the_logic_of_the_page():
    node = shutil.which("node")
    if node is None:
        pytest.skip("skipped: node is not installed")
    run = subprocess.run([node, "--test", str(Path(__file__).parent)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout[-4000:]
    assert "# fail 0" in run.stdout or "fail 0" in run.stdout
