"""Read-only bounded STA helper used under the recovery lock."""
import hashlib,json,sys
from pathlib import Path

def entity_snapshot(e):
    from src.autocad.utils import get_block_attributes
    row={'handle':e.Handle,'type':e.ObjectName,'layer':e.Layer}
    if e.ObjectName=='AcDbBlockReference':row.update(name=e.Name,attributes=get_block_attributes(e),position=list(e.InsertionPoint))
    elif e.ObjectName=='AcDbLine':row.update(start=list(e.StartPoint),end=list(e.EndPoint))
    elif e.ObjectName=='AcDbText':row.update(text=e.TextString,position=list(e.InsertionPoint),height=e.Height)
    elif e.ObjectName=='AcDbMText':row.update(text=e.TextString,position=list(e.InsertionPoint),height=e.Height,width=e.Width,rotation=e.Rotation,attachment=e.AttachmentPoint,direction=e.DrawingDirection,style=e.StyleName)
    elif e.ObjectName=='AcDbArc':row.update(center=list(e.Center),radius=e.Radius,start_angle=e.StartAngle,end_angle=e.EndAngle,normal=list(e.Normal),thickness=e.Thickness)
    elif e.ObjectName=='AcDbPolyline':
        coordinates=list(e.Coordinates)
        if len(coordinates)%2:raise ValueError('Invalid lightweight polyline coordinate count')
        count=len(coordinates)//2
        row.update(coordinates=coordinates,elevation=e.Elevation,closed=bool(e.Closed),normal=list(e.Normal),thickness=e.Thickness,
                   bulges=[e.GetBulge(i) for i in range(count)],widths=[list(e.GetWidth(i)) for i in range(count)])
    elif e.ObjectName=='AcDbCircle':row.update(center=list(e.Center),radius=e.Radius)
    else:raise ValueError('Recovery snapshot unsupported entity '+e.ObjectName)
    return row


def main():
    import pythoncom
    from src.autocad.connection import get_connection
    from src.autocad.com_runtime import wait_for_document,read_call
    from src.autocad.utils import get_block_attributes
    from src.autocad.recovery import fingerprint
    data=json.load(sys.stdin);pythoncom.CoInitialize()
    try:
        app=get_connection().get_application()
        if int(app.HWND)!=data['hwnd']:raise ValueError('Wrong instance')
        doc=wait_for_document(app,data['path'])
        def sample():
            rows=[]
            for e in doc.ModelSpace:
                rows.append(entity_snapshot(e))
            p=Path(doc.FullName)
            return {'path':str(p.resolve()),'hwnd':int(app.HWND),'saved':bool(doc.Saved),
                    'idle':bool(app.GetAcadState().IsQuiescent) and int(doc.GetVariable('CMDACTIVE'))==0,
                    'disk_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'entity_count':len(rows),'objects':rows}
        first=read_call(sample);second=read_call(sample)
        if fingerprint(first)!=fingerprint(second):raise ValueError('Drawing changed during inspection')
        print(json.dumps(second,ensure_ascii=True))
    finally:pythoncom.CoUninitialize()
if __name__=='__main__':main()
