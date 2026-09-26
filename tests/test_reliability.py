import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from src.autocad import isolated, com_runtime, lisp_bridge

@pytest.mark.parametrize('failure', ['timeout', 'tool'])
def test_read_failure_releases_gate(tmp_path, monkeypatch, failure):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    def get_active_drawing(): pass
    result={'success':False,'error':'read failed'}
    with patch.object(isolated,'run_worker',side_effect=isolated.OutcomeUnknown('timeout') if failure=='timeout' else None,return_value=result):
        first=isolated.isolated(get_active_drawing)()
        second=isolated.isolated(get_active_drawing)()
    assert first['success'] is False
    assert second.get('status') != 'previous_client_interrupted'
    assert isolated.diagnose()['marker'] is None

def test_preentry_failure_releases_write_gate(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    def draw_line(): pass
    with patch.object(isolated,'run_worker',side_effect=isolated.RequestNotSubmitted('FullName unavailable')):
        result=isolated.isolated(draw_line)()
    assert result['submitted'] is False
    assert isolated.diagnose()['marker'] is None

def test_metadata_fresh_lookup_is_bounded():
    class App:
        calls=0
        @property
        def ActiveDocument(self):
            self.calls+=1
            if self.calls<3: raise AttributeError('<unknown>.FullName')
            return SimpleNamespace(FullName='test.dwg')
    app=App()
    assert com_runtime.document_full_name(app, interval=0)=='test.dwg'
    assert app.calls==3
    with pytest.raises(AttributeError):
        com_runtime.document_full_name(App(), attempts=2, interval=0)

def test_long_expression_uses_short_single_submission(tmp_path, monkeypatch):
    monkeypatch.setattr(lisp_bridge,'ROOT',tmp_path)
    expression='(list '+ ' '.join(map(str,range(2000))) + ')'
    class Conn:
        commands=[]
        def get_active_document(self):
            return SimpleNamespace(FullName='C:/test.dwg',GetVariable=lambda _:0)
        def send_command(self, command):
            self.commands.append(command)
            source=next((tmp_path/'work/bridge').glob('*.expression'))
            assert source.read_text(encoding='utf8')==expression
            source.with_suffix('.lisp').write_text('(\"ok\" 2000)',encoding='utf8')
    conn=Conn()
    assert lisp_bridge.evaluate(conn,expression)==2000
    assert len(conn.commands)==1
    assert len(conn.commands[0].encode('utf8'))<=1900
    assert 'SECURELOAD' not in conn.commands[0]
