"""Exact object-difference allowlist for the two synthetic change fixtures."""
from copy import deepcopy

def snapshot(doc):
    from src.autocad.utils import get_block_attributes
    result={}
    for obj in doc.ModelSpace:
        row={'type':obj.ObjectName,'layer':obj.Layer}
        if obj.ObjectName=='AcDbBlockReference':
            row.update(name=obj.Name,position=list(obj.InsertionPoint),rotation=obj.Rotation,
                scale=[obj.XScaleFactor,obj.YScaleFactor,obj.ZScaleFactor],attributes=get_block_attributes(obj))
        elif obj.ObjectName=='AcDbLine':row.update(start=list(obj.StartPoint),end=list(obj.EndPoint))
        else:raise ValueError('Unsupported object in restricted change audit: '+obj.ObjectName)
        result[obj.Handle.upper()]=row
    return result

def verify(before,after,spec,report):
    if spec.get('action') not in {'lamp_green_to_red', 'output_y00_to_y01'}:
        raise ValueError('Unsupported restricted change action')
    expected=deepcopy(before);actual=deepcopy(after);component=spec['component_handle'].upper()
    if spec['action']=='lamp_green_to_red':
        old=expected.pop(component);handle=report['new_handle'].upper()
        new=actual.pop(handle)
        old['name']='HLT1R';old['attributes'].update(COLOR='RD',CAT='LAMP_24V_RED_TEST')
        if new!=old:raise RuntimeError('Replacement changed attributes or geometry outside allowed fields')
    else:
        old_wire=spec['wire_handles'][0].upper()
        old_number=report['before_wires'][0]['number_block_handle'].upper()
        expected.pop(old_wire);expected.pop(old_number)
        expected[component]['attributes'].update(X1TERM33='',X1TERM34='TEST_DO')
        new_handles=[h.upper() for h in report['new_wire']['wire_handles']]
        if len(new_handles)!=3 or len(set(new_handles))!=3:raise RuntimeError('Expected verified three-segment route')
        for handle in new_handles:
            line=actual.pop(handle)
            if line['type']!='AcDbLine' or line['layer']!='TEST_SIGNAL':raise RuntimeError('Unexpected new routing object')
        additions=set(actual)-set(expected)
        if len(additions)!=1:raise RuntimeError('Unexpected added objects after channel change')
        number=actual.pop(additions.pop())
        if number.get('name')!='WD_WNH' or number['layer']!='WIRENO' or number['attributes'].get('WIRENO')!='TEST_DO':raise RuntimeError('Unexpected new wire-number object')
    if expected!=actual:raise RuntimeError('Unrelated object changed; do not save or retry')
    return {'success':True,'unrelated_objects_unchanged':True,'before_count':len(before),'after_count':len(after)}
