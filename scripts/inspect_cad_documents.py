"""Read-only document inventory; python -m scripts.inspect_cad_documents."""
import json
import pythoncom
from src.autocad.client_gate import exclusive
from src.autocad.connection import get_connection
from src.autocad.com_runtime import document_inventory


def main():
    pythoncom.CoInitialize()
    try:
        with exclusive('inspect_document_inventory'):
            try:
                result={'success': True, 'documents': document_inventory(get_connection().get_application()),
                        'writes_submitted': False}
            except Exception as exc:
                result={'success': False, 'error': str(exc), 'writes_submitted': False}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if not result['success']:raise SystemExit(1)
    finally:
        pythoncom.CoUninitialize()


if __name__=='__main__':main()
