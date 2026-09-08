#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Station Live Telemetry Dashboard Tests (Phase 2-5)
=====================================================
Validates local loopback dashboard HTTP server, HTML5 delivery,
and REST telemetry endpoints (/api/telemetry, /api/health, /api/nodes, /api/orderbook).
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from benchmarks.dashboard.telemetry_dashboard import (
    AERDashboardServer,
    AERTelemetryProvider,
    load_dashboard_html
)


@pytest.fixture(scope="module")
def dashboard_test_server():
    """Spin up a test instance of the dashboard on an isolated test port."""
    test_port = 28749
    server = AERDashboardServer(host="127.0.0.1", port=test_port)
    _ = server.__init__("127.0.0.1", test_port)
    success = server.start()
    assert success is True, "Failed to start test dashboard server"
    time.sleep(0.1)
    yield f"http://127.0.0.1:{test_port}"
    server.stop()


def test_html_template_loader():
    """Verify HTML template loads from disk and contains branding headers."""
    html_content = load_dashboard_html()
    assert "<!DOCTYPE html>" in html_content
    assert "AER STATION" in html_content
    assert "127.0.0.1:28741" in html_content


def test_telemetry_provider_payload():
    """Verify telemetry aggregator creates complete payload with all module metrics."""
    provider = AERTelemetryProvider()
    _ = provider.__init__()
    payload = provider.get_telemetry_payload()

    assert "daemon" in payload
    assert "tpm" in payload
    assert "onchain" in payload
    assert "mesh" in payload
    assert payload["daemon"]["status"] == "ONLINE"
    assert payload["tpm"]["chip"] == "AMD_fTPM 2.0"
    assert payload["onchain"]["dispute_verifier_gas"] == 142680
    assert payload["mesh"]["total_nodes"] == 10000


def test_dashboard_html_endpoint(dashboard_test_server):
    """Verify GET / returns HTML dashboard with HTTP 200."""
    url = f"{dashboard_test_server}/"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8")
        assert "AER STATION" in body
        assert "mesh_radar_canvas" in body


def test_api_telemetry_endpoint(dashboard_test_server):
    """Verify GET /api/telemetry returns JSON telemetry with HTTP 200."""
    url = f"{dashboard_test_server}/api/telemetry"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        assert "application/json" in resp.headers.get("Content-Type", "")
        data = json.loads(resp.read().decode("utf-8"))
        assert data["daemon"]["name"] == "aerd"
        assert data["tpm"]["interface"] == "WINDOWS_TBS_API"
        assert data["mesh"]["netting_convergence_sec"] == 0.0002


def test_api_health_endpoint(dashboard_test_server):
    """Verify GET /api/health probe returns HTTP 200 OK."""
    url = f"{dashboard_test_server}/api/health"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["health"] == "OK"


def test_api_nodes_and_orderbook_endpoints(dashboard_test_server):
    """Verify GET /api/nodes and /api/orderbook return structured list data."""
    # 1. /api/nodes
    url_nodes = f"{dashboard_test_server}/api/nodes"
    with urllib.request.urlopen(url_nodes, timeout=2.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "nodes" in data
        assert len(data["nodes"]) > 0

    # 2. /api/orderbook
    url_orders = f"{dashboard_test_server}/api/orderbook"
    with urllib.request.urlopen(url_orders, timeout=2.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "orders" in data
        assert len(data["orders"]) > 0
