"""Probe configured local client launches without invoking CAD or an LLM."""
import asyncio,json,os,tomllib
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    configs={
        'codex_user':tomllib.loads((Path.home()/'.codex/config.toml').read_text(encoding='utf8'))['mcp_servers']['kinto_autocad'],
        'claude_desktop':json.loads((Path.home()/'AppData/Roaming/Claude/claude_desktop_config.json').read_text(encoding='utf8'))['mcpServers']['kinto_autocad']}
    results={}
    for label,cfg in configs.items():
        async with stdio_client(StdioServerParameters(command=cfg['command'],args=cfg.get('args',[]),cwd=cfg.get('cwd'),env={**os.environ,**cfg.get('env',{})})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=45)) as client:
                await client.initialize();listing=await client.list_tools()
                names=sorted(t.name for t in listing.tools)
                assert 'execute_trebi_batch' in names and 'get_execution_diagnostics' in names
                assert 'execute_trebi_test_change' not in names
                result=await client.call_tool('get_tool_capabilities',{})
                assert not result.isError
                results[label]={'fresh_process_handshake':True,'tools':names,'count':len(names),'desktop_ui_restart_verified':False}
    folder=Path(__file__).resolve().parents[1]/'work/client-verification';folder.mkdir(parents=True,exist_ok=True)
    (folder/'latest.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    print(json.dumps({k:{'tools':v['count'],'fresh_process_handshake':True} for k,v in results.items()}))

if __name__=='__main__':asyncio.run(main())
