"""Native measured dimensions for fixed 2D geometry; not associative constraints."""
import math
from pathlib import Path
from src.autocad.connection import get_connection
from src.autocad.utils import point3d, ensure_layer


def target(drawing_path):
    path=Path(drawing_path)
    if not path.is_absolute() or path.suffix.lower()!=".dwg":
        raise ValueError("Provide the absolute saved target DWG path")
    conn=get_connection();doc=conn.get_active_document()
    if Path(doc.FullName).resolve()!=path.resolve():raise ValueError("Active drawing differs from target")
    if int(doc.GetVariable("CMDACTIVE")):raise ValueError("CAD is busy")
    return conn,doc


def finite(*values):
    if not all(isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) for v in values):
        raise ValueError("Coordinates must be finite numbers")


def configure(obj):
    obj.TextHeight=2.5
    obj.ArrowheadSize=2.5
    obj.PrimaryUnitsPrecision=2
    obj.LinearScaleFactor=1.0
    obj.ScaleFactor=1.0
    obj.TextOverride=""
    obj.Update()


def snapshot(obj):
    if obj.ObjectName not in {"AcDbAlignedDimension","AcDbDiametricDimension"}:
        raise ValueError("Expected an aligned or diameter dimension")
    return {"success":True,"handle":obj.Handle,"object_type":obj.ObjectName,
            "measurement":float(obj.Measurement),"text_override":obj.TextOverride,
            "layer":obj.Layer,"text_height":obj.TextHeight,
            "associative":False,"note":"Native measured dimension, no automatic association to source geometry; reverify after edits"}


def aligned(drawing_path,x1,y1,x2,y2,text_x,text_y):
    created=None
    try:
        finite(x1,y1,x2,y2,text_x,text_y)
        expected=math.hypot(x2-x1,y2-y1)
        if expected==0:raise ValueError("Dimension endpoints must differ")
        conn,doc=target(drawing_path)
        ensure_layer(doc,"MCP_DIMENSIONS")
        obj=doc.ModelSpace.AddDimAligned(point3d(x1,y1),point3d(x2,y2),point3d(text_x,text_y))
        created=obj.Handle;obj.Layer="MCP_DIMENSIONS";configure(obj)
        data=snapshot(obj)
        if not math.isclose(data["measurement"],expected,abs_tol=1e-6):raise ValueError("Measurement readback mismatch")
        target(drawing_path)
        return data
    except Exception as exc:
        return {"success":False,"status":"unverified","created_handle":created,"error":str(exc)}


def diameter(drawing_path,circle_handle,leader_length=8.0):
    created=None
    try:
        finite(leader_length)
        if leader_length<=0:raise ValueError("Leader length must be positive")
        conn,doc=target(drawing_path)
        circle=doc.HandleToObject(circle_handle)
        if circle.ObjectName!="AcDbCircle":raise ValueError("Expected a circle handle")
        x,y,z=circle.Center;r=circle.Radius
        if abs(z)>1e-9 or tuple(circle.Normal)!=(0.,0.,1.):raise ValueError("Only WCS XY circles supported")
        delta=r/math.sqrt(2)
        ensure_layer(doc,"MCP_DIMENSIONS")
        obj=doc.ModelSpace.AddDimDiametric(point3d(x+delta,y+delta),point3d(x-delta,y-delta),float(leader_length))
        created=obj.Handle;obj.Layer="MCP_DIMENSIONS";configure(obj)
        data=snapshot(obj)
        if not math.isclose(data["measurement"],2*r,abs_tol=1e-6):raise ValueError("Diameter readback mismatch")
        target(drawing_path)
        return {**data,"source_circle":circle_handle}
    except Exception as exc:
        return {"success":False,"status":"unverified","created_handle":created,"error":str(exc)}


def inspect(drawing_path,handle):
    try:
        _,doc=target(drawing_path)
        return snapshot(doc.HandleToObject(handle))
    except Exception as exc:
        return {"success":False,"error":str(exc)}
