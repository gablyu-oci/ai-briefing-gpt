#!/usr/bin/env python3
"""
serve.py — HTTP server for previewing briefings and serving admin dashboard.

Usage:
  python3 scripts/serve.py
  python3 scripts/serve.py --port 9000
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import OUTPUT_ROOT, SERVER_PORT


def find_latest_briefing() -> str | None:
    """Return the path to the latest index.html relative to OUTPUT_DIR."""
    if not OUTPUT_ROOT.exists():
        return None
    dated_dirs = sorted(
        [d for d in OUTPUT_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")],
        reverse=True,
    )
    for d in dated_dirs:
        idx = d / "index.html"
        if idx.exists():
            return f"{d.name}/index.html"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve OCI briefing + admin dashboard")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Port to serve on")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    try:
        import uvicorn
        from app.api.routes import app
        from fastapi.staticfiles import StaticFiles

        # Mount output directory for static file serving
        if OUTPUT_ROOT.exists():
            app.mount("/output", StaticFiles(directory=str(OUTPUT_ROOT)), name="output")

        latest = find_latest_briefing()
        print(f"Starting server at http://localhost:{args.port}")
        print(f"Admin dashboard: http://localhost:{args.port}/admin")
        if latest:
            print(f"Latest briefing: http://localhost:{args.port}/output/{latest}")

        if not args.no_browser:
            import webbrowser
            import threading
            url = f"http://localhost:{args.port}/admin"
            threading.Timer(1.0, webbrowser.open, args=[url]).start()

        uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")

    except ImportError:
        # Fallback to simple HTTP server if FastAPI/uvicorn not available
        import http.server
        import os
        import socketserver

        print("FastAPI/uvicorn not available. Falling back to simple HTTP server.")
        os.chdir(str(OUTPUT_ROOT))

        handler = http.server.SimpleHTTPRequestHandler
        handler.log_message = lambda *a: None

        try:
            with socketserver.TCPServer(("", args.port), handler) as httpd:
                httpd.allow_reuse_address = True
                print(f"Serving at http://localhost:{args.port}")
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
