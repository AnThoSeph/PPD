"""Local static file server for the web UI."""

from __future__ import annotations

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_web_server(web_root: Path) -> tuple[str, ThreadingHTTPServer]:
    port = _free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=str(web_root))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{port}/index.html", server
