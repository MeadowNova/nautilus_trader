"""Simple HTTP proxy that forwards Prometheus metrics requests."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

TARGET_HOST = os.getenv("TARGET_HOST", "ai_metrics")
TARGET_PORT = int(os.getenv("TARGET_PORT", "9100"))
PROXY_PORT = int(os.getenv("PROXY_PORT", "9101"))


class MetricsProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        upstream = f"http://{TARGET_HOST}:{TARGET_PORT}/metrics"
        response = requests.get(upstream, timeout=10)
        payload = response.content

        self.send_response(response.status_code)
        self.send_header("Content-Type", response.headers.get("Content-Type", "text/plain"))
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PROXY_PORT), MetricsProxyHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
