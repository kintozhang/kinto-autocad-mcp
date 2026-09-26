"""Opt-in empty TREBI-layout DWG acceptance. No source circuit is changed."""
from pathlib import Path
from datetime import datetime
import json,shutil,sys
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document
from src.autocad.client_gate import exclusive
from src.autocad.trebi_titleblock import install_empty_seed
from scripts.verify_pdf_project import lookup_saved_close
ROOT=Path(__file__).resolve().parents[1]

def main():
 assert '--write' in sys.argv
 folder=ROOT/'work/acceptance'/datetime.now().strftime('trebi-frame-%Y%m%d-%H%M%S');folder.mkdir()
 path=folder/'KINTO-TREBI-ELECTRICAL-A3.dwg'
 values={'REV':'A','CHANGES':'模板验证 / Frame test','REV_DATE':'2026-09-25','SIGNATURE':'TEST','BRAND':'KINTO ENGINEERING','PLAN':'KINTO-TREBI-TEST','ORDER':'TEST','CUSTOMER':'TEST','DESCRIPTION':'电气模板验证 / Electrical frame test','PLANNER':'KINTO','DATE':'2026-09-25','PAGE':'102','OF':'96','PREV':'101','NEXT':'103'}
 report={'status':'RUNNING','drawing':str(path),'values':values}
 try:
  with exclusive('trebi-empty-frame-acceptance'):
   shutil.copy2(ROOT/'work/projects/bilingual-20260924-221032/KINTO-A3-ZH-EN-SEED-221509.dwg',path)
   conn=get_connection();app=conn.get_application()
   read_call(lambda:app.Documents.Open)(str(path));wait_for_document(app,path)
   report['install']=install_empty_seed(conn,path,values)
   doc=conn.get_active_document();assert doc.ModelSpace.Count==2
   doc.Save();lookup_saved_close(app,path)(False)
   read_call(lambda:app.Documents.Open)(str(path));doc=wait_for_document(app,path)
   block=doc.HandleToObject(report['install']['handle'])
   actual={a.TagString:a.TextString for a in block.GetAttributes()}
   assert actual==values and doc.ModelSpace.Count==2
   report.update(status='PASS',save_reopen='PASS',entity_count=2,native_grid='PENDING',units=doc.GetVariable('INSUNITS'))
 except Exception as exc:
  report.update(status='FAILED',error=str(exc));raise
 finally:
  (folder/'report.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf8');print(folder,flush=True)
if __name__=='__main__':main()
