#!/usr/bin/env python3
"""Run VerifyIntern on this machine, with nothing to install.

    python tools/serve.py

Builds the site, serves it, and opens it in your browser. Press Ctrl+C to
stop. Standard library only: no pip, no virtualenv, no API needed.
"""
from __future__ import annotations

import argparse
import http.server
import socketserver
import threading
import webbrowser
from functools import partial


from build_site import ROOT, build  # noqa: E402  (same directory)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Same as the stdlib handler, minus a log line for every asset."""

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        if args and str(args[0]).startswith(("GET /", "POST /")) and " 200 " in " ".join(map(str, args)):
            return
        super().log_message(fmt, *args)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-browser", action="store_true", help="Don't open a browser window")
    args = ap.parse_args()

    site = ROOT / "site"
    build(site, repo=None)

    handler = partial(QuietHandler, directory=str(site))
    socketserver.TCPServer.allow_reuse_address = True

    port = args.port
    for attempt in range(10):
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            port += 1
    else:
        raise SystemExit(f"Could not find a free port near {args.port}.")

    url = f"http://127.0.0.1:{port}/"
    print(f"\nVerifyIntern is running at {url}")
    print("Press Ctrl+C to stop.\n")

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
