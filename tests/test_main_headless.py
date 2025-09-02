from __future__ import annotations

import os
import subprocess
import sys


def test_headless_entrypoint_exits_successfully():
    # Run module as script in headless mode with small step count
    env = os.environ.copy()
    env["AMOR_HEADLESS"] = "1"
    cmd = [sys.executable, "-m", "amor_mortuorum", "--max-steps", "3", "--tick-rate", "0"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=20)

    assert proc.returncode == 0, proc.stderr
    assert "Amor Mortuorum - MVP (headless)" in proc.stdout
    assert "Loop complete (steps=3)" in proc.stdout
