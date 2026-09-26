from pathlib import Path
from unittest.mock import patch
import pytest
from src.autocad.worker import validate_target,PreflightRejected
from src.autocad.isolated import isolated,diagnose,RequestNotSubmitted

@pytest.mark.parametrize('expected,argument',[
 ({'hwnd':8},''),({'hwnd':-1},''),({'hwnd':True},''),
 ({'drawing_path':'relative.dwg'},''),({'drawing_path':'C:/wrong.dwg'},''),
 ({},'C:/wrong.dwg')])
def test_target_mismatch_rejected(expected,argument):
    with pytest.raises(PreflightRejected):
        validate_target('C:/correct.dwg',7,expected,argument)


def test_matching_target():
    validate_target('C:/correct.dwg',7,{'drawing_path':'C:/correct.dwg','hwnd':7},'C:/correct.dwg')


def test_known_preflight_rejection_does_not_quarantine(tmp_path):
    def example():raise AssertionError('never called in parent')
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), \
         patch('src.autocad.isolated.run_worker',side_effect=[RequestNotSubmitted('mismatch'),{'success':True}]) as worker:
        wrapped=isolated(example)
        result=wrapped(expected_drawing_path='C:/wrong.dwg',expected_instance_hwnd=7)
        assert result['submitted'] is False
        assert diagnose()['marker'] is None
        assert diagnose()['recent_operations'][0]['state']=='not_submitted'
        assert wrapped()['success']
        assert worker.call_args_list[0].args[0]['expected']=={'drawing_path':'C:/wrong.dwg','hwnd':7}
