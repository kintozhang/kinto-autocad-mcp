"""Native WDT project-field update on fresh copies of bilingual fixtures."""
from pathlib import Path
from datetime import datetime
import json,re,shutil,sys
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document
from src.autocad.lisp_bridge import evaluate,literal
from scripts.bilingual_smoke import circuit

ROOT=Path(__file__).resolve().parents[1]


def main():
 assert '--write' in sys.argv
 source=ROOT/'work/projects/bilingual-20260924-221032'
 folder=ROOT/'work/projects'/datetime.now().strftime('title-mapping-%Y%m%d-%H%M%S');folder.mkdir()
 wdp=folder/(folder.name+'.wdp');data=(source/(source.name+'.wdp')).read_text(encoding='utf-8-sig')
 data=re.sub(r'^\*\[1\].*$', '*[1]KINTO NATIVE TITLE TEST',data,flags=re.M)
 data=re.sub(r'^\*\[10\].*$', '*[10]B',data,flags=re.M)
 assert data.splitlines()[0]=='*[1]KINTO NATIVE TITLE TEST'
 pages=[]
 for suffix in ['01-SUPPLY.dwg','02-CONTROL.dwg','03-CONTACT.dwg']:
  old=source/(source.name+'-'+suffix);page=folder/(folder.name+'-'+suffix)
  shutil.copy2(old,page);data=data.replace(old.name,page.name);pages.append(page)
 wdp.write_text(data,encoding='utf-8-sig');shutil.copy2(ROOT/'profiles/titleblock-zh-en.wdt',wdp.with_suffix('.wdt'))
 c=get_connection();app=c.get_application();report={'status':'RUNNING','project':str(wdp),'pages':[]}
 def record():(folder/'mapping-acceptance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
 def read(fn):return read_call(fn,label='title mapping snapshot')
 try:
  docs=[]
  for page in pages:
   doc=read(lambda:app.Documents.Open)(str(page));wait_for_document(app,page);docs.append(doc)
  for index,(page,doc) in enumerate(zip(pages,docs),1):
   doc.Activate();wait_for_document(app,page)
   evaluate(c,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
   before=read(lambda:circuit(doc))
   blocks=read(lambda:[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name=='KINTO_TB_A3_ZH_EN'])
   assert len(blocks)==1;handle=read(lambda:blocks[0].Handle)
   attrs=lambda:{a.TagString:a.TextString for a in doc.HandleToObject(handle).GetAttributes()}
   prior=read(attrs)
   # Official 2026 API: 16 drawing toggles; then zero-based LINE1/LINE10 indexes.
   flags=[0]*16;flags[7]=1
   evaluate(c,'(progn (c:wd_tb_process_one 1 '+literal([flags,0,9])+') T)',timeout=30)
   actual=read(attrs)
   expected={**prior,'PROJECT':'KINTO NATIVE TITLE TEST','REV':'B','SHEET':str(index)}
   item={'drawing':str(page),'before':prior,'after':actual};report['pages'].append(item);record()
   assert actual==expected,actual
   assert read(lambda:circuit(doc))==before
   doc.Save();doc.Close(False)
   doc=read(lambda:app.Documents.Open)(str(page));wait_for_document(app,page)
   assert read(attrs)==expected and read(lambda:circuit(doc))==before
   item.update(save_reopen='PASS',circuit_unchanged=True);record()
  report['status']='PASS'
 except Exception as exc:report.update(status='FAILED',error=str(exc));raise
 finally:record();print(folder,flush=True)


if __name__=='__main__':main()
