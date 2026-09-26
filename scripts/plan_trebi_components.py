"""Print offline page and device-tag plans; no CAD writes."""
import json,sys
from pathlib import Path
from src.autocad.trebi_project_pages import plan
from src.autocad.trebi_component_tags import plan_tags
if __name__=='__main__':
    manifest=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
    components=json.loads(Path(sys.argv[2]).read_text(encoding='utf8'))
    print(json.dumps({'pages':plan(manifest),'devices':plan_tags(manifest,components)},ensure_ascii=True,indent=2))
