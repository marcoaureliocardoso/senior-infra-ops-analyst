#!/usr/bin/env python3
"""Disposable loopback HTTP fixture that never records headers or bodies."""
from __future__ import annotations

import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MAX_BODY_BYTES = 64 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--request-log", type=Path, required=True)
    return parser.parse_args()


def handler_for(request_log: Path) -> type[BaseHTTPRequestHandler]:
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def record(self) -> None:
            with lock, request_log.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(f"{self.command} {self.path}\n")

        def finish_with(self, status: int) -> None:
            self.record()
            self.send_response(status)
            self.end_headers()

        def do_GET(self) -> None:
            self.finish_with(204 if self.path == "/health" else 404)

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.finish_with(400)
                return
            if length < 0 or length > MAX_BODY_BYTES:
                self.finish_with(413)
                return
            if length:
                self.rfile.read(length)
            self.finish_with(204 if self.path == "/reload" else 404)

    return Handler


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(args.request_log))
    args.ready_file.write_text(str(server.server_port), encoding="utf-8")
    server.serve_forever()


if __name__ == "__main__":
    main()
