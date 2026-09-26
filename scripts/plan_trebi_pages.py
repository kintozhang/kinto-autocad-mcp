"""Print title-field plan from an explicit manifest; does not write CAD."""
import json
import sys
from pathlib import Path
from src.autocad.trebi_project_pages import plan
if __name__=="__main__":
    result=plan(json.loads(Path(sys.argv[1]).read_text(encoding="utf8")))
    print(json.dumps(result,ensure_ascii=True,indent=2))
