"""Bounded worker lifetime; timeout is never interpreted as a rolled-back CAD write."""
from functools import wraps
import inspect
import json
from pathlib import Path
import subprocess
import sys
import uuid
from src.autocad.client_gate import exclusive, GateRejected, gate_path

ROOT = Path(__file__).resolve().parents[2]
DEADLINE = 45
TOOL_DEADLINES = {"execute_trebi_test_change": 180, "execute_trebi_batch": 600, "export_electrical_project_report": 90, "export_electrical_project_pdf": 180}

METADATA = {"get_tool_capabilities", "get_symbol_list", "get_autocad_info"}

READ_ONLY = METADATA | {"get_active_drawing", "list_drawings", "get_project_info"}

class RequestNotSubmitted(RuntimeError):
    pass

class OutcomeUnknown(RuntimeError):
    pass


def run_worker(request, timeout=DEADLINE):
    proc = subprocess.Popen([sys.executable, "-m", "src.autocad.worker"], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        output, errors = proc.communicate(json.dumps(request), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()  # Only this helper; never acad.exe.
        proc.communicate(timeout=5)
        raise OutcomeUnknown("worker_timeout") from None
    if proc.returncode:
        raise OutcomeUnknown("worker_failed: " + errors[-1000:])
    try:
        result = json.loads(output)
    except (ValueError, TypeError):
        raise OutcomeUnknown("invalid_worker_receipt") from None
    if not isinstance(result, dict):
        raise OutcomeUnknown("invalid_worker_receipt")
    if result.get("phase") == "not_entered":
        raise RequestNotSubmitted(result.get("error", "Target preflight rejected"))
    if result.get("phase") != "completed" or not isinstance(result.get("result"), dict):
        raise OutcomeUnknown("invalid_worker_envelope")
    return result["result"]


def isolated(function):
    signature = inspect.signature(function, eval_str=True)
    parameters = list(signature.parameters.values())
    if function.__name__ not in METADATA:
        parameters += [inspect.Parameter("expected_drawing_path", inspect.Parameter.KEYWORD_ONLY, default="", annotation=str),
                       inspect.Parameter("expected_instance_hwnd", inspect.Parameter.KEYWORD_ONLY, default=0, annotation=int)]
    public_signature = signature.replace(parameters=parameters)
    @wraps(function)
    def call(*args, **kwargs):
        public_signature.bind(*args, **kwargs)
        expected = {"drawing_path": kwargs.pop("expected_drawing_path", ""),
                    "hwnd": kwargs.pop("expected_instance_hwnd", 0)}
        bound = inspect.signature(function).bind(*args, **kwargs)
        operation_id = uuid.uuid4().hex
        record = {"operation_id": operation_id, "tool": function.__name__, "state": "starting"}
        folder = gate_path().parent / "operations"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (operation_id + ".json")
        def save():
            progress = path.with_suffix(".progress")
            if progress.exists():
                try: record["worker"] = json.loads(progress.read_text(encoding="utf8"))
                except (OSError, ValueError): record["worker"] = {"state": "unreadable_progress"}
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(record, ensure_ascii=True, indent=2), encoding="utf8")
            temporary.replace(path)
        try:
            with exclusive(function.__name__ + ":" + operation_id):
                save()
                try:
                    result = run_worker({"tool": function.__name__, "arguments": bound.arguments,
                                         "expected": expected,
                                         "progress_path": str(path.with_suffix(".progress"))},
                                        timeout=TOOL_DEADLINES.get(function.__name__, DEADLINE))
                except RequestNotSubmitted as exc:
                    result = {"success": False, "status": "target_rejected", "submitted": False,
                              "error": str(exc), "operation_id": operation_id}
                    record.update(state="not_submitted", result=result)
                    save()
                    return result
                except OutcomeUnknown as exc:
                    if function.__name__ not in READ_ONLY:
                        raise
                    result = {"success": False, "status": "read_failed", "submitted": False,
                              "error": str(exc), "operation_id": operation_id}
                record["result"] = result
                if result.get("success") is False and function.__name__ in READ_ONLY:
                    record["state"] = "read_failed"
                    save()
                    return result
                if function.__name__ in {"execute_trebi_batch", "execute_trebi_test_change"} and result.get("status") == "preflight_rejected" and result.get("submitted") is False:
                    record["state"] = "not_submitted"
                    save()
                    return result
                if result.get("success") is False:
                    raise OutcomeUnknown("tool_reported_failure; inspect before retry")
                record["state"] = "completed"
                save()
                return result
        except GateRejected as exc:
            return {"success": False, "status": exc.status, "submitted": False}
        except Exception as exc:
            record.update(state="outcome_unknown", error=str(exc))
            save()
            return {"success": False, "status": "outcome_unknown", "submitted": "unknown",
                    "operation_id": operation_id, "error": str(exc), "automatic_retry": False}
    call.__signature__ = public_signature
    call.__doc__ = (function.__doc__ or "") + " Optional expected_drawing_path and expected_instance_hwnd are checked before tool entry; mismatch never switches drawings."
    return call


def diagnose():
    """Read local receipts only, including during a held/quarantined gate."""
    path = gate_path()
    marker = None
    if path.exists():
        with path.open("rb") as stream:
            stream.seek(1)
            content = stream.read()
        if content:
            try: marker = json.loads(content)
            except ValueError: marker = {"state": "incomplete_marker"}
    folder = path.parent / "operations"
    recent = []
    if folder.exists():
        for receipt in sorted(folder.glob("*.json"), key=lambda p:p.stat().st_mtime, reverse=True)[:10]:
            try:
                item = json.loads(receipt.read_text(encoding="utf8"))
                progress = receipt.with_suffix(".progress")
                if progress.exists():
                    item["worker"] = json.loads(progress.read_text(encoding="utf8"))
                recent.append(item)
            except (OSError, ValueError): recent.append({"receipt": str(receipt), "state": "unreadable"})
    return {"success": True, "cad_contacted": False, "marker": marker, "recent_operations": recent,
            "note": "Marker alone does not distinguish running from interrupted. No recovery or retry performed."}


def async_isolated(function):
    """Keep stdio responsive while its owned helper runs; cancellation does not replay work."""
    import asyncio
    invoke = isolated(function)
    @wraps(function)
    async def call(*args, **kwargs):
        return await asyncio.to_thread(invoke, *args, **kwargs)
    call.__signature__ = inspect.signature(invoke)
    call.__doc__ = invoke.__doc__
    return call
