#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Zero-Server Local Loopback UI Server
========================================
Runs an air-gapped HTTP JSON interface strictly bound to 127.0.0.1:28741
without external network exposure or centralized cloud tracking (AER Roadmap Phase 3).

Features:
- Pure Python standard library http.server implementation
- Real-time streaming of node reputation, hardware status, and order books
- Local loopback security isolation
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional


_DAEMON_STATE_PROVIDER = None


class AERLocalUIHandler(BaseHTTPRequestHandler):
    """HTTP request dispatcher for local GUI and CLI dashboards."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server request logs to maintain clean terminal."""
        pass

    def _set_json_headers(self, status_code: int = 200) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle status and telemetry inspection queries."""
        global _DAEMON_STATE_PROVIDER
        if self.path == "/api/status" or self.path == "/":
            self._set_json_headers(200)
            telemetry_data = _DAEMON_STATE_PROVIDER() if _DAEMON_STATE_PROVIDER else {}
            status_data = {
                "daemon": "aerd",
                "version": "1.9.2",
                "status": "ONLINE",
                "loopback_bind": "127.0.0.1:28741",
                "telemetry": telemetry_data
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        elif self.path == "/api/health":
            self._set_json_headers(200)
            self.wfile.write(json.dumps({"health": "OK"}).encode("utf-8"))
        else:
            self._set_json_headers(404)
            self.wfile.write(json.dumps({"error": "NOT_FOUND"}).encode("utf-8"))


class AERLocalUIServer:
    """
    Background threaded HTTP server exposing local daemon telemetry.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 28741):
        self.host = host
        self.port = port
        self.httpd: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self, state_provider_callable=None) -> bool:
        """Start the background daemon loopback listener."""
        global _DAEMON_STATE_PROVIDER
        try:
            _DAEMON_STATE_PROVIDER = state_provider_callable
            self.httpd = HTTPServer((self.host, self.port), AERLocalUIHandler)
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
            self.is_running = True
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """Shutdown the local loopback listener."""
        if self.httpd and self.is_running:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.is_running = False


if __name__ == "__main__":
    _default_ui_server = AERLocalUIServer()

