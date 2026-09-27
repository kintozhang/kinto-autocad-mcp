"""Internal AutoLISP bridge with a unique, completed receipt per request."""
from __future__ import annotations
import json
import math
from pathlib import Path
import re
import threading
import time
import uuid
from src.autocad.com_runtime import read_document_name, read_call, wait_for_document

_LOCK = threading.RLock()
ROOT = Path(__file__).resolve().parents[2]


class BridgeError(RuntimeError):
    pass


def literal(value):
    if value is None:
        return "nil"
    if isinstance(value, str):
        if any(ord(c) < 32 for c in value):
            raise ValueError("Control characters are not allowed in CAD strings")
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("Coordinates must be finite")
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "(list " + " ".join(literal(v) for v in value) + ")"
    raise ValueError("Unsupported Lisp argument")


def parse_receipt(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    pos = 0
    def read():
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("Incomplete receipt")
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            items = []
            while pos < len(tokens) and tokens[pos] != ")":
                items.append(read())
            if pos >= len(tokens):
                raise ValueError("Unclosed receipt")
            pos += 1
            return items
        if tok == ")":
            raise ValueError("Unexpected closing parenthesis")
        if tok.startswith('"'):
            return json.loads(tok)
        if tok.lower() == "nil":
            return None
        if tok == "T":
            return True
        try:
            return float(tok) if any(c in tok.lower() for c in ".e") else int(tok)
        except ValueError:
            raise ValueError("Unsupported receipt atom: " + tok) from None
    value = read()
    if pos != len(tokens):
        raise ValueError("Trailing receipt content")
    return value


def evaluate(conn, expression, timeout=15):
    """Only internal constructed expressions; not exposed as an arbitrary MCP tool.

    Receipts prove completion, not business correctness. CAD COM SendCommand itself
    can block; this polling timeout is not a hard COM call deadline.
    """
    with _LOCK:
        doc = conn.get_active_document()
        name = read_call(lambda:doc.FullName)
        if not name:
            raise BridgeError("Save the test drawing before using Electrical APIs")
        if int(read_call(lambda:doc.GetVariable("CMDACTIVE"))):
            raise BridgeError("A CAD command is active; inspect it before continuing")
        wait_for_document(conn.get_application(),name)
        folder = ROOT / "work" / "bridge"
        folder.mkdir(parents=True, exist_ok=True)
        operation = uuid.uuid4().hex
        result_file = folder / (operation + ".lisp")
        # Long expressions travel as a private UTF-8 data file. The short command
        # reads it completely and closes it before evaluation. No SECURELOAD or
        # trusted-path changes, and no replay after an uncertain submission.
        if len(expression.encode("utf8")) > 700:
            source_file = folder / (operation + ".expression")
            source_file.write_text(expression, encoding="utf8")
            expression = (
                '((lambda (/ ks kl kt) (setq kt "" ks (open '
                + literal(source_file.as_posix()) + ' "r" "utf8")) '
                '(if (null ks) (error "Cannot open bridge expression")) '
                '(while (setq kl (read-line ks)) (setq kt (strcat kt kl "\\n"))) '
                '(close ks) (eval (read kt))))')
        target = name.replace("\\", "/").upper()
        # The document check executes inside CAD, immediately before the operation.
        guarded = ('(if (= (strcase (vl-string-translate "\\\\" "/" '
                   '(strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) '
                   + literal(target) + ') ' + expression
                   + ' (error "Target drawing changed"))')
        command = (
            '((lambda (/ kresult kfile) '
            "(setq kresult (vl-catch-all-apply '(lambda () " + guarded + ') nil)) '
            '(setq kfile (open ' + literal(result_file.as_posix()) + ' "w" "utf8")) '
            '(if kfile (progn '
            '(prin1 (if (vl-catch-all-error-p kresult) '
            '(list "error" (vl-catch-all-error-message kresult)) (list "ok" kresult)) kfile) '
            '(close kfile))) (princ)))\n'
        )
        if len(command.encode("utf8")) > 1900:
            raise BridgeError("Bridge command exceeds safe input length; nothing submitted")
        conn.send_command(command)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if result_file.exists():
                try:
                    status, value = parse_receipt(result_file.read_text(encoding="utf-8-sig"))
                except (ValueError, OSError):
                    time.sleep(.05)
                    continue
                if status != "ok":
                    raise BridgeError(f"CAD API error [{operation}]: {value}")
                if read_document_name(conn.get_active_document) != name:
                    raise BridgeError(f"Document changed after operation [{operation}]; inspect before retry")
                wait_for_document(conn.get_application(),name)
                return value
            time.sleep(.05)
        raise BridgeError(f"Completion unknown [{operation}]; inspect CAD and receipt before retrying")