from types import SimpleNamespace
from src.tools.native_electrical import _points

class Busy(Exception):
    hresult=-2147418111

class Block:
    def __init__(self):self.calls=0
    def GetAttributes(self):
        self.calls+=1
        if self.calls==1:raise Busy('busy read')
        return [SimpleNamespace(TagString='X4TERM01J',InsertionPoint=(1,2,0)),SimpleNamespace(TagString='TERM01J',TextString='4'),SimpleNamespace(TagString='X1TERMDESC01J',TextString='not a connection'),SimpleNamespace(TagString='X1TERM02P',InsertionPoint=(3,4,0)),SimpleNamespace(TagString='TERM02P',TextString='6')]

def test_retry_entire_read_only_point_snapshot_and_exclude_description():
    block=Block();result=_points(block)
    assert block.calls==2
    assert result==[{'connection':'X4TERM01J','position':[1,2,0],'terminal':'4'},{'connection':'X1TERM02P','position':[3,4,0],'terminal':'6'}]
