#!/usr/bin/env python3
"""Disposable loopback HTTP fixture that never records header values or bodies."""
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
    parser.add_argument("--redirect-ready-file", type=Path)
    parser.add_argument("--redirect-observation-log", type=Path)
    return parser.parse_args()


def handler_for(
    request_log: Path, redirect_port: int | None = None
) -> type[BaseHTTPRequestHandler]:
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
            if self.path == "/redirect" and redirect_port is not None:
                self.record()
                self.send_response(302)
                self.send_header(
                    "Location", f"http://127.0.0.1:{redirect_port}/capture"
                )
                self.end_headers()
                return
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


def redirect_handler_for(
    request_log: Path, observation_log: Path
) -> type[BaseHTTPRequestHandler]:
    lock = threading.Lock()

    class RedirectDestinationHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            with lock, request_log.open(
                "a", encoding="utf-8", newline="\n"
            ) as stream:
                stream.write(f"{self.command} {self.path}\n")
            observed = self.headers.get("X-Vault-Token") is not None
            observation_log.write_text(
                f"X-Vault-Token={'present' if observed else 'absent'}\n",
                encoding="utf-8",
            )
            self.send_response(204 if self.path == "/capture" else 404)
            self.end_headers()

    return RedirectDestinationHandler


def main() -> None:
    args = parse_args()
    redirect_server = None
    redirect_port = None
    if args.redirect_ready_file is not None:
        if args.redirect_observation_log is None:
            raise SystemExit("--redirect-observation-log is required")
        redirect_server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            redirect_handler_for(args.request_log, args.redirect_observation_log),
        )
        redirect_port = redirect_server.server_port
        args.redirect_ready_file.write_text(str(redirect_port), encoding="utf-8")
        threading.Thread(target=redirect_server.serve_forever, daemon=True).start()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), handler_for(args.request_log, redirect_port)
    )
    args.ready_file.write_text(str(server.server_port), encoding="utf-8")
    try:
        server.serve_forever()
    finally:
        if redirect_server is not None:
            redirect_server.shutdown()
            redirect_server.server_close()


if __name__ == "__main__":
    main()
