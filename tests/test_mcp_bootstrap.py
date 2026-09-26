"""Exercise the real stdio protocol without connecting to or modifying CAD."""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_initializes_and_lists_tools_without_model_credentials():
    root = Path(__file__).resolve().parents[1]
    child = """
import os
from unittest.mock import patch
for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'KINTO_MCP_EXPERIMENTAL'):
    os.environ.pop(name, None)
from src.autocad.detector import AutoCADInfo
with patch('src.autocad.detector.detect', return_value=AutoCADInfo()):
    import src.server as server
with patch.object(server, '_attempt_autocad_connect'):
    server.main()
"""

    async def check():
        params = StdioServerParameters(command=sys.executable, args=['-c', child], cwd=str(root))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=20)) as session:
                await session.initialize()
                result = await session.list_tools()
                names = {tool.name for tool in result.tools}
                from src.tool_policy import catalogue
                assert names == {name for name,item in catalogue().items() if item["default_enabled"]}
                metadata = {"get_autocad_info", "get_symbol_list", "get_tool_capabilities", "get_execution_diagnostics", "plan_trebi_batch", "plan_delta_r2_io"}
                for tool in result.tools:
                    if tool.name not in metadata:
                        properties = tool.inputSchema["properties"]
                        assert properties["expected_drawing_path"]["type"] == "string"
                        assert properties["expected_instance_hwnd"]["type"] == "integer"
                import json
                recipe = json.loads((root/'examples/trebi-batch.json').read_text(encoding='utf8'))
                preview = await session.call_tool('plan_trebi_batch', {'spec': recipe})
                data = preview.structuredContent or json.loads(next(c.text for c in preview.content if c.type=='text'))
                assert data['success'] and data['submitted'] is False
                assert data['pages']['effective_drawing_count'] == 2
                io_spec=json.loads((root/'examples/delta-r2-io-plan.json').read_text(encoding='utf8'))
                io_reply=await session.call_tool('plan_delta_r2_io',{'spec':io_spec})
                io_data=io_reply.structuredContent or json.loads(next(c.text for c in io_reply.content if c.type=='text'))
                assert io_data['success'] and not io_data['cad_contacted'] and not io_data['ready_for_drawing']
                assert io_data['signals'][1]['electrical_type']=='relay_no_dry_contact'
                assert "create_wire_from_to" not in names
                assert "move_component" not in names
                result = await session.call_tool("create_wire_from_to", {"from_component":"A","to_component":"B"})
                assert result.isError


    asyncio.run(asyncio.wait_for(check(), timeout=30))