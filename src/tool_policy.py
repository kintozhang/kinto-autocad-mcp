"""Single source of truth for default MCP exposure; unknown tools fail closed."""
import json
import inspect
from functools import wraps
from mcp.types import CallToolResult, TextContent
import os
from pathlib import Path
from src.autocad.isolated import async_isolated
CAPABILITIES=Path(__file__).resolve().parents[1]/"profiles/tool-capabilities.json"


def catalogue():
    return json.loads(CAPABILITIES.read_text(encoding="utf8"))["tools"]


def protocol_result(function):
    @wraps(function)
    async def invoke(*args, **kwargs):
        result = function(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, dict):
            return CallToolResult(isError=result.get("success") is False, structuredContent=result,
                content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))])
        return result
    invoke.__signature__ = inspect.signature(function, eval_str=True).replace(return_annotation=CallToolResult)
    return invoke


def register(mcp):
    def tool():
        def decorate(function):
            entry=catalogue().get(function.__name__)
            if entry is None:
                raise RuntimeError("Missing tool capability entry: "+function.__name__)
            if entry["default_enabled"] or os.environ.get("KINTO_MCP_EXPERIMENTAL")=="1":
                return mcp.tool()(protocol_result(function if function.__name__ in {"get_execution_diagnostics", "plan_trebi_batch", "plan_delta_r2_io", "plan_cad_project", "audit_cad_project", "restore_cad_project"} else async_isolated(function)))
            return function
        return decorate
    return tool
