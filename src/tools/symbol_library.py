"""Read actual installed DWG files; file existence is not semantic validation."""
import os
from pathlib import Path
DEFAULT_LIBRARY=Path(r"C:\Users\Public\Documents\Autodesk\Acade 2026\Libs\iec2")
VERIFIED={"coils":{"HCR1"},"terminals":{"HT0001"},"fuses":{"HFU1"},"buttons":{"HPB11"},"signals":{"HA1S1","HA1D3"},"contacts":{"HCR21","HCR22"}}


def list_symbols(category="", library_path=None, query="", limit=100, offset=0):
    try:
        if not 1<=limit<=200 or offset<0:
            raise ValueError("limit must be 1..200 and offset nonnegative")
        folder=Path(library_path or os.environ.get("KINTO_SYMBOL_LIBRARY") or DEFAULT_LIBRARY).resolve()
        if not folder.is_dir():raise ValueError("Symbol library folder does not exist")
        names=VERIFIED.get(category.lower(),set()) if category else None
        files=sorted((p for p in folder.glob("*.dwg") if (names is None or p.stem.upper() in names) and query.lower() in p.stem.lower()),key=lambda p:p.name.lower())
        known=set().union(*VERIFIED.values())
        items=[{"name":p.stem,"path":str(p),"file_exists":True,
                "live_sample_verified":folder==DEFAULT_LIBRARY.resolve() and p.stem.upper() in known}
               for p in files[offset:offset+limit]]
        return {"success":True,"library":str(folder),"category":category or "all", "symbols":[i["name"] for i in items],
                "items":items,"count":len(items),"total":len(files),"offset":offset,
                "next_offset":offset+len(items) if offset+len(items)<len(files) else None,
                "category_scope":"Categories cover named verified samples only; all/query search real files without claiming semantic coverage"}
    except Exception as exc:
        return {"success":False,"error":str(exc)}
