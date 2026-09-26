"""Private one-request STA executable. No model API and no arbitrary code input."""
import inspect
import json
import sys
from contextlib import redirect_stdout


class PreflightRejected(ValueError):
    pass


def validate_target(original, hwnd, expected, drawing_path=""):
    from pathlib import Path
    requested_hwnd = expected.get("hwnd", 0)
    if isinstance(requested_hwnd, bool) or not isinstance(requested_hwnd, int) or requested_hwnd < 0:
        raise PreflightRejected("Expected HWND must be a nonnegative integer")
    if requested_hwnd and requested_hwnd != hwnd:
        raise PreflightRejected("Requested AutoCAD instance is not the attached instance")
    for value in (expected.get("drawing_path", ""), drawing_path):
        if value:
            path = Path(value)
            if not path.is_absolute() or path.suffix.lower() != ".dwg":
                raise PreflightRejected("Expected drawing must be an absolute DWG path")
            if path.resolve() != Path(original).resolve():
                raise PreflightRejected("Requested drawing is not active; tool not entered")


def main():
    request = json.load(sys.stdin)
    import os
    from pathlib import Path
    def progress(state, **fields):
        if request.get("progress_path"):
            path = Path(request["progress_path"])
            data = {"pid": os.getpid(), "state": state, **fields}
            temporary = path.with_suffix(".progress-tmp")
            temporary.write_text(json.dumps(data), encoding="utf8")
            temporary.replace(path)
    progress("starting")
    import pythoncom
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    entered = False
    try:
        with redirect_stdout(sys.stderr):
            from src import server
            from src.tool_policy import catalogue
            from src.autocad.connection import get_connection
            from src.autocad.com_runtime import read_call, document_full_name
            name = request["tool"]
            if name not in catalogue():
                raise ValueError("Unknown tool")
            function = inspect.unwrap(getattr(server, name))
            args = request["arguments"]
            inspect.signature(function).bind(**args)
            metadata = {"get_tool_capabilities", "get_symbol_list", "get_autocad_info"}
            if name not in metadata:
                conn = get_connection()
                app = conn.get_application()
                # One connection instance is retained throughout this worker.
                hwnd = read_call(lambda: int(app.HWND))
                original = document_full_name(app)
                progress("target_bound", drawing_path=original, hwnd=hwnd)
                try:
                    validate_target(original, hwnd, request.get("expected", {}), args.get("drawing_path", ""))
                except PreflightRejected as exc:
                    progress("not_entered", drawing_path=original, hwnd=hwnd, error=str(exc))
                    # stdout is redirected here; emit the protocol through its saved stream.
                    sys.__stdout__.write(json.dumps({"phase": "not_entered", "error": str(exc)}))
                    return
                # PDF intentionally switches to copies; it has its own per-page guards.
                if name not in {"export_electrical_project_pdf", "execute_trebi_batch"}:
                    conn._bound_document = original
                    conn._bound_hwnd = hwnd
            progress("tool_entering")
            entered = True
            result = function(**args)
            if name not in metadata:
                if read_call(lambda: int(app.HWND)) != hwnd:
                    raise ValueError("AutoCAD instance changed")
                if document_full_name(app) != original:
                    raise ValueError("Active document changed during operation")
        print(json.dumps({"phase": "completed", "result": result}, ensure_ascii=True))
    except Exception as exc:
        if entered:
            raise
        progress("not_entered", error=str(exc))
        print(json.dumps({"phase": "not_entered", "error": str(exc)}))
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    main()
