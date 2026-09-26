"""Fail-fast Windows process gate for cooperating MCP servers of one user."""
from contextlib import contextmanager
from functools import wraps
import json
import os
from pathlib import Path
import time


class GateRejected(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(status)


def gate_path():
    # Shared across checkouts and Codex/Claude; deliberately no per-client override.
    return Path(os.environ["LOCALAPPDATA"]) / "KintoAutoCADMCP" / "session.lock"


@contextmanager
def exclusive(operation, *, path=None):
    import msvcrt
    path = Path(path) if path is not None else gate_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Lock byte zero even in a new empty file; metadata lives after that byte.
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_BINARY, 0o600)
    with os.fdopen(fd, "r+b", buffering=0) as stream:
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise GateRejected("cad_in_use") from exc
        try:
            stream.seek(1)
            if stream.read():
                raise GateRejected("previous_client_interrupted")
            stream.seek(1)
            stream.write(json.dumps({"pid": os.getpid(), "operation": operation,
                                     "started": time.time()}).encode("utf8"))
            os.fsync(stream.fileno())
            # Uncaught exceptions and process death intentionally retain the marker.
            yield
            stream.seek(1)
            stream.truncate()
            os.fsync(stream.fileno())
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def guarded(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            with exclusive(function.__name__):
                return function(*args, **kwargs)
        except GateRejected as exc:
            return {"success": False, "status": exc.status, "submitted": False,
                    "message": "Request was not submitted. Inspect CAD state before retrying; "
                               "an interrupted-client marker requires manual recovery."}
    return call
