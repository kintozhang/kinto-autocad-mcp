"""CLI for the shared verified PDF merger."""
import argparse
import json
from pathlib import Path
from src.autocad.pdf_merge import fingerprint, merge


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('manifest'); parser.add_argument('output')
    args = parser.parse_args()
    result = merge(args.manifest, args.output)
    Path(args.output).with_suffix('.verification.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

