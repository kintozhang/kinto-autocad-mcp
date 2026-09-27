"""Internal TREBI PDF navigation from native attribute bounds, never text guessing."""
import math
import re
from pypdf.annotations import Link
from pypdf.generic import Fit

def collect(doc, title_name):
    from src.autocad.com_runtime import read_attribute_metadata
    return read_attribute_metadata(lambda:_collect_once(doc,title_name),label="complete PDF navigation snapshot")


def _collect_once(doc, title_name):
    links=[]
    for obj in doc.ModelSpace:
        if obj.ObjectName!='AcDbBlockReference' or not obj.HasAttributes: continue
        attrs=list(obj.GetAttributes()); values={a.TagString:a.TextString for a in attrs}
        title=obj.Name==title_name
        for a in attrs:
            if title and a.TagString in {'PREV','NEXT'}:
                if a.TextString=='-':continue
                target=a.TextString;zone=None;kind='page_navigation'
                if not re.fullmatch(r'0|[1-9][0-9]*',target):raise ValueError('Invalid title navigation page')
            elif values.get('SIGCODE') and a.TagString=='XREF':
                match=re.fullmatch(r'(0|[1-9][0-9]*)\.([0-9])',a.TextString)
                if not match:raise ValueError('Unsupported signal reference: '+a.TextString)
                target,zone=match.group(1),int(match.group(2));kind='signal_reference'
            else:continue
            if a.Invisible:raise ValueError('Navigation attribute is invisible')
            low,high=a.GetBoundingBox()
            bounds=[float(low[0]),float(low[1]),float(high[0]),float(high[1])]
            if not all(math.isfinite(v) for v in bounds) or not (10<=bounds[0]<bounds[2]<=410 and 10<=bounds[1]<bounds[3]<=289):
                raise ValueError('Navigation attribute outside verified frame')
            links.append(dict(kind=kind,label=a.TextString,target_page=target,zone=zone,bounds_mm=bounds,handle=obj.Handle,attribute=a.TagString))
    return {'schema_version':1,'links':links,'scope':'signal_XREF_and_title_PREV_NEXT'}

def frame_bounds(page):
    """Find the 400x279 mm native frame among PDF vector paths, excluding clip bounds."""
    vertical=[];horizontal=[];last=None;start=None
    def visit(op,args,cm,tm):
        nonlocal last,start
        def point(x,y):
            x,y=float(x),float(y);a,b,c,d,e,f=map(float,cm)
            return (a*x+c*y+e,b*x+d*y+f)
        def segment(a,b):
            if abs(a[0]-b[0])<.02 and abs(a[1]-b[1])>400:vertical.append((a[0],min(a[1],b[1]),max(a[1],b[1])))
            if abs(a[1]-b[1])<.02 and abs(a[0]-b[0])>500:horizontal.append((a[1],min(a[0],b[0]),max(a[0],b[0])))
        if op==b'm':last=start=point(*args)
        elif op==b'l':
            current=point(*args)
            if last is not None:segment(last,current)
            last=current
        elif op==b'h' and last is not None and start is not None:segment(last,start);last=start
        elif op==b're':
            x,y,w,h=map(float,args);points=[point(x,y),point(x+w,y),point(x+w,y+h),point(x,y+h)]
            for a,b in zip(points,points[1:]+points[:1]):segment(a,b)
            last=start=points[0]
        elif op in {b'n',b'S',b's',b'f',b'f*',b'B',b'B*'}:last=start=None
    page.extract_text(visitor_operand_before=visit)
    candidates=[]
    for x,y0,y1 in vertical:
        for xx,yy0,yy1 in vertical:
            if xx<=x or abs(yy0-y0)>.1 or abs(yy1-y1)>.1:continue
            if abs((xx-x)/(y1-y0)-400/279)>.001:continue
            if not all(any(abs(hy-y)<.1 and abs(hx-x)<.1 and abs(hxx-xx)<.1 for hy,hx,hxx in horizontal) for y in (y0,y1)):continue
            rect=(x,y0,xx,y1)
            if not any(max(abs(a-b) for a,b in zip(rect,r))<.2 for r in candidates):candidates.append(rect)
    if len(candidates)!=1:raise ValueError('Cannot uniquely calibrate TREBI PDF frame')
    return candidates[0]

def point(frame,x,y):
    l,b,r,t=frame
    return (l+(x-10)*(r-l)/400,b+(y-10)*(t-b)/279)

def add_navigation(writer,entries):
    enabled=[e.get('navigation') is not None for e in entries]
    if not any(enabled):return {'status':'not_requested','links':[],'bookmarks':[]}
    if not all(enabled):raise ValueError('Incomplete navigation metadata')
    logical=[e.get('logical_page') for e in entries]
    if any(not isinstance(v,str) or not re.fullmatch(r'0|[1-9][0-9]*',v) for v in logical) or len(set(logical))!=len(logical):raise ValueError('Unique logical PDF pages required')
    frames=[frame_bounds(p) for p in writer.pages];targets={v:i for i,v in enumerate(logical)};records=[]
    for i,entry in enumerate(entries):
        if entry['navigation'].get('schema_version')!=1:raise ValueError('Unknown PDF navigation schema')
        writer.add_outline_item('PAGE '+logical[i],i,fit=Fit.fit())
        for link in entry['navigation']['links']:
            if link['target_page'] not in targets:raise ValueError('Reference target absent from exported project: '+link['target_page'])
            j=targets[link['target_page']];zone=link['zone'];bounds=link['bounds_mm']
            if zone is not None and (type(zone) is not int or not 0<=zone<=9):raise ValueError('Invalid reference zone')
            if len(bounds)!=4 or not all(type(v) in (float,int) and math.isfinite(v) for v in bounds) or not (10<=bounds[0]<bounds[2]<=410 and 10<=bounds[1]<bounds[3]<=289):raise ValueError('Invalid click bounds')
            lo=point(frames[i],bounds[0],bounds[1]);hi=point(frames[i],bounds[2],bounds[3]);rect=[lo[0]-2,lo[1]-2,hi[0]+2,hi[1]+2]
            if zone is None:fit=Fit.fit()
            else:
                l,b=point(frames[j],10+zone*40,40);r,t=point(frames[j],50+zone*40,283)
                fit=Fit.fit_rectangle(l,b,r,t)
            annotation=writer.add_annotation(i,Link(rect=rect,target_page_index=j,fit=fit))
            annotation['/Dest'][0]=writer.pages[j].indirect_reference
            records.append(dict(source_pdf_page=i+1,target_pdf_page=j+1,target_logical_page=link['target_page'],label=link['label'],zone=zone,rect=rect,fit_type=str(fit.fit_type),fit_args=[float(v) for v in fit.fit_args]))
    return {'status':'created','links':records,'bookmarks':logical,'frame_bounds':frames}

def verify(reader,expected):
    if expected['status']=='not_requested':return
    actual=[]
    refs={p.indirect_reference.idnum:i+1 for i,p in enumerate(reader.pages)}
    for i,p in enumerate(reader.pages):
        for ref in p.get('/Annots',[]):
            a=ref.get_object()
            if a.get('/Subtype')!='/Link':continue
            dest=a.get('/Dest')
            if not dest or '/A' in a:raise ValueError('Expected internal PDF destination only')
            actual.append((i+1,refs[dest[0].idnum],tuple(float(x) for x in a['/Rect']),str(dest[1]),tuple(float(v) for v in dest[2:])))
    wanted=[(r['source_pdf_page'],r['target_pdf_page'],tuple(r['rect']),r['fit_type'],tuple(r['fit_args'])) for r in expected['links']]
    if len(actual)!=len(wanted) or any(a[:2]!=b[:2] or a[3]!=b[3] or len(a[4])!=len(b[4]) or any(abs(x-y)>1e-5 for x,y in zip(a[4],b[4])) or any(abs(x-y)>1e-5 for x,y in zip(a[2],b[2])) for a,b in zip(actual,wanted)):raise ValueError('PDF link readback mismatch')
    outlines=reader.outline
    if [o.title for o in outlines]!=['PAGE '+p for p in expected['bookmarks']] or [reader.get_destination_page_number(o) for o in outlines]!=list(range(len(outlines))):raise ValueError('PDF bookmark readback mismatch')
