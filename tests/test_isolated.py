import inspect
import json
import subprocess
import sys
import time
from unittest.mock import MagicMock,patch
import pytest
from src.autocad.isolated import isolated,diagnose,run_worker,OutcomeUnknown
from src.autocad.connection import AutoCADConnection,AutoCADConnectionError


def test_timeout_kills_only_owned_helper_and_keeps_quarantine(tmp_path):
    real_popen=subprocess.Popen
    children=[]
    def spawn(*args,**kwargs):
        child=real_popen([sys.executable,'-c','import time; time.sleep(30)'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8')
        children.append(child)
        return child
    def fake_tool():
        pytest.fail('parent must not execute CAD function')
    from src.autocad import isolated as module
    original=module.run_worker
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.isolated.subprocess.Popen',side_effect=spawn), \
         patch('src.autocad.isolated.run_worker',side_effect=lambda req,**kw:original(req,timeout=.1)):
        start=time.monotonic()
        result=isolated(fake_tool)()
        assert time.monotonic()-start<5
        assert result['status']=='outcome_unknown' and not result['automatic_retry']
        assert children[0].poll() is not None
        assert isolated(fake_tool)()['status']=='previous_client_interrupted'
        assert len(children)==1
        info=diagnose()
        assert info['cad_contacted'] is False and info['marker']
        assert info['recent_operations'][0]['state']=='outcome_unknown'


def test_success_and_signature(tmp_path):
    def example(value:float=1)->dict:return {}
    wrapper=isolated(example)
    assert inspect.signature(wrapper).parameters["value"]==inspect.signature(example).parameters["value"]
    assert "expected_drawing_path" in inspect.signature(wrapper).parameters
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.isolated.run_worker',return_value={'success':True,'handle':'1'}) as worker:
        assert wrapper(2)['handle']=='1'
        assert wrapper(3)['success']
        assert worker.call_count==2
        assert diagnose()['marker'] is None


def test_failed_tool_result_remains_available_and_blocks_retry(tmp_path):
    def example():pass
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.isolated.run_worker',return_value={'success':False,'error':'partial'}) as worker:
        assert isolated(example)()['status']=='outcome_unknown'
        assert isolated(example)()['status']=='previous_client_interrupted'
        assert worker.call_count==1
        assert diagnose()['recent_operations'][0]['result']['error']=='partial'


@pytest.mark.parametrize('changed',['document','instance'])
def test_bound_connection_rejects_changed_target(changed,tmp_path):
    conn=AutoCADConnection()
    app=MagicMock();conn._app=app
    expected=str(tmp_path/'one.dwg')
    conn._bound_document=expected;conn._bound_hwnd=123
    app.HWND=124 if changed=='instance' else 123
    app.ActiveDocument.FullName=str(tmp_path/'two.dwg') if changed=='document' else expected
    with pytest.raises(AutoCADConnectionError,match='Bound'):
        conn.send_command('test')
    app.ActiveDocument.SendCommand.assert_not_called()


def test_async_dispatch_leaves_event_loop_responsive(tmp_path):
    import asyncio
    import threading
    from src.autocad.isolated import async_isolated
    entered=threading.Event()
    release=threading.Event()
    def worker(*args,**kwargs):
        entered.set()
        assert release.wait(5)
        return {"success":True}
    def example(): pass
    async def run():
        task=asyncio.create_task(async_isolated(example)())
        try:
            for _ in range(100):
                if entered.is_set():break
                await asyncio.sleep(.01)
            assert entered.is_set() and not task.done()
            assert diagnose()["marker"]
        finally:
            release.set()
        assert (await task)["success"]
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.isolated.run_worker',side_effect=worker):
        asyncio.run(run())
