import asyncio
from datetime import timedelta
import os
from pathlib import Path
import sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.client_gate import exclusive


def test_diagnostics_remains_callable_over_stdio_while_gate_held(tmp_path):
    child='''
from unittest.mock import patch
from src.autocad.detector import AutoCADInfo
with patch('src.autocad.detector.detect',return_value=AutoCADInfo()):
    from src import server
server.main()
'''
    async def run():
        params=StdioServerParameters(command=sys.executable,args=['-c',child],
            cwd=str(Path(__file__).resolve().parents[1]),env={**os.environ,'LOCALAPPDATA':str(tmp_path),'KINTO_MCP_EXPERIMENTAL':'0'})
        with exclusive('test-holder',path=tmp_path/'KintoAutoCADMCP/session.lock'):
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=15)) as s:
                    await s.initialize()
                    result=await s.call_tool('get_active_drawing',{})
                    assert result.structuredContent.get('status')=='cad_in_use', result
                    assert result.isError
                    result=await s.call_tool('get_execution_diagnostics',{})
                    assert result.structuredContent['cad_contacted'] is False
                    assert result.structuredContent['marker']['operation']=='test-holder'
    asyncio.run(run())


def test_startup_detection_never_uses_com_when_disabled():
    from unittest.mock import patch
    from src.autocad import detector
    def process(info):
        info.running=True
        info.variant='unknown'
    with patch.object(detector,'_detect_via_registry'), \
         patch.object(detector,'_detect_running_process',side_effect=process), \
         patch.object(detector,'_detect_via_com') as com:
        detector.detect(force=True,allow_com=False)
        com.assert_not_called()
    detector._cached_detect.cache_clear()
