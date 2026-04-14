#!/usr/bin/env python3
"""
serve.py — Simple HTTP server for viewing generated briefings in a browser.

Usage:
  python3 serve.py
  python3 serve.py --port 9000

Opens http://localhost:8000 (or specified port) and lists available briefings.
"""

import argparse
import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"


def find_latest_briefing() -> str | None:
    """Return the path to the latest index.html relative to OUTPUT_DIR."""
    if not OUTPUT_DIR.exists():
        return None
    dated_dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")],
        reverse=True,
    )
    for d in dated_dirs:
        idx = d / "index.html"
        if idx.exists():
            return f"{d.name}/index.html"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve OCI briefing output directory")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    if not OUTPUT_DIR.exists():
        print(f"ERROR: Output directory not found: {OUTPUT_DIR}")
        print("       Run `python3 main.py --dry-run` first to generate a briefing.")
        sys.exit(1)

    latest = find_latest_briefing()
    url = f"http://localhost:{args.port}"
    if latest:
        open_url = f"{url}/{latest}"
        print(f"Serving at {url}")
        print(f"Latest briefing: {open_url}")
    else:
        open_url = url
        print(f"Serving at {url}")
        print("No briefings found yet. Run main.py to generate one.")

    os.chdir(str(OUTPUT_DIR))

    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a: None  # suppress request logging

    try:
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            httpd.allow_reuse_address = True
            if not args.no_browser:
                webbrowser.open(open_url)
            print(f"Press Ctrl+C to stop.")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.port} is already in use. Try --port 9000")
        else:
            raise


if __name__ == "__main__":
    main()
