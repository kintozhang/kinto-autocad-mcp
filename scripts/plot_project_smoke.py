"""CLI for synthetic snapshot plotting; implementation shared with MCP."""
import argparse
from src.autocad.project_plot import project_pages, digest, plot_snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project'); parser.add_argument('staging')
    parser.add_argument('--write', action='store_true', required=True)
    args = parser.parse_args()
    import win32com.client
    app = win32com.client.GetActiveObject('AutoCAD.Application')
    print(plot_snapshot(args.project, args.staging, app))


if __name__ == '__main__':
    main()
