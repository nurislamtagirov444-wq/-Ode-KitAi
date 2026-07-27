"""Мини-сервер, который притворяется OpenAI-совместимым API.

Нужен только для проверки, что цепочка провайдеров реально ходит по HTTP.
В обычной работе не используется.

Запуск: python3 tests/fake_server.py [порт] [режим]
режимы: ok | ratelimit
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

MODE = "ok"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # тише в тестах
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        request = json.loads(body) if body else {}

        if MODE == "ratelimit":
            payload = {"error": {"message": "Rate limit reached for model", "code": 429}}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        payload = {
            "id": "chatcmpl-fake",
            "model": request.get("model", "fake-model"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "фейковый ответ: ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 4},
        }
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    global MODE
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    MODE = sys.argv[2] if len(sys.argv) > 2 else "ok"
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"fake server on 127.0.0.1:{port} mode={MODE}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
