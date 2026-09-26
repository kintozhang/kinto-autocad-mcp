"""Opt-in live MCP geometry test. Only writes a newly created synthetic DWG."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Create and save a new synthetic test DWG')
    args = parser.parse_args()
    if not args.write:
        parser.error('Pass --write to run the explicitly requested live drawing test')
    import pythoncom
    import win32com.client
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    output = ROOT / 'work' / 'acceptance' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, exist_ok=False)
    path = output / 'mcp-plate-120x80.dwg'
    report = {'output': str(path), 'status': 'started', 'tools': []}
    pythoncom.CoInitialize()
    try:
        app = win32com.client.GetActiveObject('AutoCAD.Application')
        report['version'] = str(app.Version)
        report['original_documents'] = [str(d.Name) for d in app.Documents]
        doc = app.Documents.Add()
        doc.SetVariable('INSUNITS', 4)
        doc.SaveAs(str(path))
        if doc.ModelSpace.Count != 0:
            raise RuntimeError('Template contains model entities; refusing ambiguous test')

        def guard():
            if Path(app.ActiveDocument.FullName).resolve() != path.resolve():
                raise RuntimeError('Active document changed; stopped before the next operation')
            if int(doc.GetVariable('CMDACTIVE')) != 0:
                raise RuntimeError('CAD command still active; do not blindly retry')

        async def exercise():
            params = StdioServerParameters(command=sys.executable, args=['-m','src.server'], cwd=str(ROOT))
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=30)) as session:
                    await session.initialize()
                    async def call(name, arguments):
                        guard()
                        result = await session.call_tool(name, arguments)
                        data = result.structuredContent
                        if data is None:
                            data = json.loads(next(c.text for c in result.content if c.type == 'text'))
                        report['tools'].append({'tool':name, 'arguments':arguments, 'result':data})
                        if result.isError or data.get('success') is False:
                            raise RuntimeError(f'{name}: {data}')
                        return data
                    await call('get_active_drawing', {})
                    rectangle = await call('draw_rectangle', {'x1':0,'y1':0,'x2':120,'y2':80,'layer':'MCP_OUTLINE'})
                    circles = []
                    for x,y in [(10,10),(110,10),(110,70),(10,70)]:
                        c = await call('draw_circle', {'cx':x,'cy':y,'radius':3,'layer':'MCP_HOLES'})
                        circles.append((c['handle'],x,y))
                    label = await call('draw_text', {'x':0,'y':88,'text':'KINTO MCP TEST - 120 x 80 mm / 4 x DIA 6','height':4,'layer':'MCP_TEXT'})
                    await call('zoom_extents', {})
                    await call('get_active_drawing', {})
                    return rectangle['handle'], circles, label['handle']

        rect_handle, circles, text_handle = asyncio.run(exercise())
        def verify(document):
            assert document.ModelSpace.Count == 6, document.ModelSpace.Count
            rect = document.HandleToObject(rect_handle)
            assert rect.Closed
            assert math.isclose(rect.Area, 9600, abs_tol=1e-6)
            assert list(rect.Coordinates) == [0,0,120,0,120,80,0,80]
            for handle,x,y in circles:
                circle = document.HandleToObject(handle)
                assert list(circle.Center) == [x,y,0]
                assert math.isclose(circle.Radius, 3, abs_tol=1e-9)
                assert circle.Layer == 'MCP_HOLES'
            assert document.HandleToObject(text_handle).TextString.startswith('KINTO MCP TEST')
            assert int(document.GetVariable('INSUNITS')) == 4
            return {'entities':6, 'plate_mm':[120,80], 'hole_diameter_mm':6, 'hole_centres_mm':[[x,y] for _,x,y in circles], 'units':'mm'}
        guard()
        report['before_reopen'] = verify(doc)
        doc.Save()
        doc.Close(False)  # Already saved and verified; closes only this test document.
        doc = app.Documents.Open(str(path))
        report['after_reopen'] = verify(doc)
        app.ZoomExtents()
        report['status'] = 'passed'
    except BaseException as exc:
        report['status'] = 'failed'
        report['error'] = repr(exc)
        raise
    finally:
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'status':report['status'],'report':str(output/'report.json'),'drawing':str(path)},ensure_ascii=False),flush=True)
        pythoncom.CoUninitialize()


if __name__ == '__main__':
    run()