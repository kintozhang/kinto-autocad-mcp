"""Normalize an AutoCAD plot copy, removing malformed XMP; preserve page streams."""
import argparse,hashlib,json
from pathlib import Path
from pypdf import PdfReader,PdfWriter

def streams(reader):
    return [hashlib.sha256(p.get_contents().get_data()).hexdigest() for p in reader.pages]

def main():
    p=argparse.ArgumentParser();p.add_argument("source");p.add_argument("output");args=p.parse_args()
    source,output=Path(args.source).resolve(),Path(args.output).resolve()
    assert source!=output and not output.exists(),"Use distinct existing source and new output"
    r=PdfReader(source);before=streams(r);sizes=[list(page.mediabox) for page in r.pages]
    # XMP is document metadata, not drawing content. Keep the raw native PDF separately.
    r.root_object.pop("/Metadata",None)
    w=PdfWriter();w.clone_document_from_reader(r);w.pdf_header=r.pdf_header
    with output.open("wb") as f:w.write(f)
    after=PdfReader(output,strict=True)
    assert streams(after)==before and [list(page.mediabox) for page in after.pages]==sizes
    print(json.dumps({"pages":len(after.pages),"page_content_unchanged":True,"page_sizes_points":sizes,"output":str(output)}))

if __name__=="__main__":main()
