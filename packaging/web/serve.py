#!/usr/bin/env python3
"""Serve the CADCraft web build with a plain Python web server.

    python3 packaging/web/serve.py            # dist/web (build: cd apps/cadcraft-web && trunk build --release)
    python3 packaging/web/serve.py <folder>   # any static folder, e.g. an unpacked cadcraft-web-<ver>/ bundle
    python3 serve.py                         # from inside an unpacked bundle

Serves on http://localhost:8765 by default; --port and --bind change that. Standard
library only, Python 3.8+. Sends what a static CADCraft site needs (see the hosting
notes in this folder): .wasm as application/wasm, immutable caching on content-hashed
assets, and no-cache on index.html. It does not compress; for real hosting, gzip or
brotli the .wasm (about 13 MB down to about 5 MB).
"""
import argparse
import os
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 8765
HASHED = re.compile(r"-[0-9a-f]{8,}")  # trunk's content-hash segment in built asset names


class CadcraftHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler with CADCraft's MIME and caching rules."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",  # browsers refuse to stream-compile it under any other type
        ".js": "text/javascript",
    }

    def end_headers(self):
        name = os.path.basename(self.translate_path(self.path))
        if name == "index.html" or not HASHED.search(name):
            self.send_header("Cache-Control", "no-cache")  # the page and unhashed files always revalidate
        else:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")  # hashed assets
        super().end_headers()


def default_directory():
    """An unpacked bundle (index.html next to this script) serves itself; a checkout serves dist/web."""
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isfile(os.path.join(here, "index.html")):
        return here
    return os.path.normpath(os.path.join(here, os.pardir, os.pardir, "dist", "web"))


def main():
    parser = argparse.ArgumentParser(description="Serve the CADCraft web build (static site).")
    parser.add_argument("directory", nargs="?", default=None,
                        help="folder to serve (default: dist/web in a checkout, this folder in a bundle)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"port to listen on (default {DEFAULT_PORT})")
    parser.add_argument("--bind", default="127.0.0.1",
                        help="address to bind (default 127.0.0.1; 0.0.0.0 for the LAN)")
    args = parser.parse_args()

    directory = args.directory or default_directory()
    if not os.path.isfile(os.path.join(directory, "index.html")):
        sys.exit(f"error: no index.html in {directory}\n"
                 "       build the web app first:  cd apps/cadcraft-web && trunk build --release\n"
                 "       or pass a folder:  python3 packaging/web/serve.py cadcraft-web-<ver>/")

    server = ThreadingHTTPServer((args.bind, args.port), partial(CadcraftHandler, directory=directory))
    host = "localhost" if args.bind in ("127.0.0.1", "localhost", "::1") else args.bind
    print(f"CADCraft web serving {directory}")
    print(f"  open http://{host}:{args.port}/  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
