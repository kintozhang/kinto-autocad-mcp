from types import SimpleNamespace
import pytest
from src.autocad.utils import get_block_attributes

class Busy(Exception):
    hresult = -2147418111

class TransientAttribute:
    TagString = "PAGE"
    def __init__(self): self.calls = 0
    @property
    def TextString(self):
        self.calls += 1
        if self.calls == 1: raise Busy("busy")
        return "405"

def test_busy_property_retries_whole_snapshot():
    attr = TransientAttribute()
    block = SimpleNamespace(GetAttributes=lambda: [SimpleNamespace(TagString="OF",TextString="1"),attr])
    assert get_block_attributes(block) == {"OF":"1","PAGE":"405"}
    assert attr.calls == 2

def test_nonbusy_failure_is_not_hidden_as_partial_attributes():
    class Bad:
        TagString = "PAGE"
        @property
        def TextString(self): raise ValueError("unreadable")
    block = SimpleNamespace(GetAttributes=lambda: [SimpleNamespace(TagString="OF",TextString="1"),Bad()])
    with pytest.raises(ValueError,match="unreadable"): get_block_attributes(block)
