#!/usr/bin/env python3
"""Loopback-only Anthropic Messages mock with a measurable user-word limit."""
from __future__ import annotations

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def user_word_count(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    texts: list[str] = []
    for message in value.get("messages", []):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    texts.append(block["text"])
    return len(re.findall(r"\S+", " ".join(texts)))


def main() -> int:
    if len(sys.argv) != 5:
        return 2
    port_path, log_path = map(Path, sys.argv[1:3])
    reported_window, observed_window = map(int, sys.argv[3:5])
    if not (1 <= observed_window < reported_window <= 10_000_000):
        return 2

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            status = 400
            safe_path = urlsplit(self.path).path
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16 * 1024 * 1024:
                    raise ValueError("invalid bounded body")
                value = json.loads(self.rfile.read(length))
                input_words = user_word_count(value)
                accepted = safe_path == "/v1/messages" and input_words <= observed_window
                status = 200 if accepted else 400
                if accepted and value.get("stream") is True:
                    chunks = [
                        {"type":"message_start","message":{"id":"msg_mock","type":"message","role":"assistant","model":"mock-model","content":[],"stop_reason":None,"stop_sequence":None,"usage":{"input_tokens":input_words,"output_tokens":0}}},
                        {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}},
                        {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"P004A_MOCK_OK"}},
                        {"type":"content_block_stop","index":0},
                        {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":None},"usage":{"output_tokens":1}},
                        {"type":"message_stop"},
                    ]
                    body = "".join(f"event: {item['type']}\ndata: {json.dumps(item, separators=(',', ':'))}\n\n" for item in chunks).encode()
                    content_type = "text/event-stream"
                elif accepted:
                    body = json.dumps({
                        "id":"msg_mock","type":"message","role":"assistant","model":"mock-model",
                        "content":[{"type":"text","text":"P004A_MOCK_OK"}],
                        "stop_reason":"end_turn","stop_sequence":None,
                        "usage":{"input_tokens":input_words,"output_tokens":1},
                    }, separators=(",", ":")).encode()
                    content_type = "application/json"
                else:
                    body = json.dumps({
                        "type":"error","error":{"type":"invalid_request_error","message":"mock observed window exceeded"},
                    }, separators=(",", ":")).encode()
                    content_type = "application/json"
            except (ValueError, json.JSONDecodeError, TypeError):
                body = b'{"type":"error","error":{"type":"invalid_request_error","message":"invalid mock request"}}'
                content_type = "application/json"
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({
                    "method":"POST", "path":safe_path, "status":status,
                    "reportedWindow":reported_window, "observedWindow":observed_window,
                }, separators=(",", ":")) + "\n")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port_path.write_text(json.dumps({"port": server.server_port}) + "\n", encoding="utf-8")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
