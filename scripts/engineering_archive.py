"""Run with python -m scripts.engineering_archive."""
import argparse
import json
from src.autocad.engineering_archive import backup, verify, restore, receipt_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('backup'); p.add_argument('source'); p.add_argument('destination'); p.add_argument('files', nargs='+')
    p = sub.add_parser('verify'); p.add_argument('archive')
    p = sub.add_parser('restore'); p.add_argument('archive'); p.add_argument('destination')
    p = sub.add_parser('receipts'); p.add_argument('paths', nargs='+')
    args = vars(parser.parse_args()); command = args.pop('command')
    result = {'backup': backup, 'verify': verify, 'restore': restore, 'receipts': receipt_summary}[command](**args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
