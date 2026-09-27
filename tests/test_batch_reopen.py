import pytest
from src.tools.batch_reopen import validate_saved_targets

@pytest.mark.parametrize('fault',[None,'unsaved','readonly','missing','duplicate'])
def test_only_exact_saved_targets_can_close(fault,tmp_path):
    p=str(tmp_path/'test.dwg');metadata=[dict(path=p,saved=True,read_only=False)]
    if fault=='unsaved':metadata[0]['saved']=False
    if fault=='readonly':metadata[0]['read_only']=True
    if fault=='missing':metadata=[]
    if fault=='duplicate':metadata*=2
    if fault:
        with pytest.raises(ValueError):validate_saved_targets(metadata,[p])
    else:validate_saved_targets(metadata,[p])

def test_unrelated_unsaved_drawing_is_not_closed(tmp_path):
    p=str(tmp_path/'test.dwg')
    validate_saved_targets([dict(path=p,saved=True,read_only=False),dict(path=str(tmp_path/'user.dwg'),saved=False,read_only=False)],[p])
