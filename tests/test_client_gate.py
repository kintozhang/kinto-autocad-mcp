import inspect
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from src.autocad.client_gate import exclusive, guarded, GateRejected

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows file locking")


def test_competing_process_is_rejected_then_can_acquire(tmp_path):
    path = tmp_path / "gate"
    code = "from src.autocad.client_gate import exclusive; import sys\nwith exclusive('child', path=sys.argv[1]):\n print('acquired')"
    with exclusive("parent", path=path):
        result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True)
        assert result.returncode != 0 and b"cad_in_use" in result.stderr
    result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True)
    assert result.returncode == 0, result.stderr


def test_crash_remains_blocked_across_repeated_attempts(tmp_path):
    path = tmp_path / "gate"
    code = "from src.autocad.client_gate import exclusive; import sys,os\nwith exclusive('crash', path=sys.argv[1]):\n os._exit(7)"
    result = subprocess.run([sys.executable, "-c", code, str(path)])
    assert result.returncode == 7
    for _ in range(2):
        with pytest.raises(GateRejected, match="previous_client_interrupted"):
            with exclusive("next", path=path):
                pytest.fail("must not execute")


def test_exception_keeps_uncertainty_marker(tmp_path):
    path = tmp_path / "gate"
    with pytest.raises(ValueError):
        with exclusive("failed", path=path):
            raise ValueError("uncertain")
    with pytest.raises(GateRejected, match="previous_client_interrupted"):
        with exclusive("next", path=path):
            pytest.fail("must not execute")


def test_wrapper_preserves_schema_and_never_enters_body_on_conflict(tmp_path):
    path = tmp_path / "gate"
    calls = []
    def example(x: float, radius: float = 2) -> dict:
        """Example tool."""
        calls.append(x)
        return {"success": True}
    wrapped = guarded(example)
    assert inspect.signature(wrapped) == inspect.signature(example)
    assert wrapped.__name__ == example.__name__ and wrapped.__doc__ == example.__doc__
    with patch("src.autocad.client_gate.gate_path", return_value=path):
        with exclusive("other", path=path):
            assert wrapped(1) == {"success": False, "status": "cad_in_use", "submitted": False,
                "message": "Request was not submitted. Inspect CAD state before retrying; "
                           "an interrupted-client marker requires manual recovery."}
            assert calls == []
        assert wrapped(1)["success"]
    assert calls == [1]
