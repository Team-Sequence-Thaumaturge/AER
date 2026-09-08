#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Trinity End-to-End Integration Tests (Phase 3-4)
===================================================
Cross-validates the Trinity Triad interfaces:
1. Retro TTY BBS Console (Cyberpunk Operator Interface)
2. Zero-Dependency MCP Gateway (Autonomous Agent Standard IO Interface)
3. HTML5/REST Live Telemetry Dashboard (Real-time Web Action Panel)

Ensures consistent state, unified telemetry, non-blocking asynchronous actions,
and deterministic execution across all three operator modalities.
"""

import os
import sys
import io
import json
import time
import urllib.request
import pytest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.dashboard.telemetry_dashboard import AERDashboardServer
from aer.console import AERInteractiveConsole
from aer.mcp_server import AERProductionMCPServer
from aer.bounty import BountyManager, BountyStatus


@pytest.fixture(scope="module")
def trinity_dashboard_server():
    """Spin up an isolated dashboard server for Trinity E2E tests on port 28751."""
    test_port = 28751
    server = AERDashboardServer(host="127.0.0.1", port=test_port)
    _ = server.__init__("127.0.0.1", test_port)
    success = server.start()
    assert success is True, "Failed to start Trinity E2E dashboard server"
    time.sleep(0.1)
    yield f"http://127.0.0.1:{test_port}"
    server.stop()


def test_trinity_telemetry_consistency(trinity_dashboard_server):
    """
    Verify that MCP Server, Dashboard REST API, and TTY Console
    report coherent core telemetry metrics and status.
    """
    # 1. MCP Gateway Telemetry Call
    mcp = AERProductionMCPServer()
    mcp_call = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/call",
        "params": {
            "name": "aer_get_telemetry",
            "arguments": {}
        }
    }
    mcp_resp = mcp.handle_jsonrpc(mcp_call)
    assert mcp_resp["id"] == 101
    mcp_payload = json.loads(mcp_resp["result"]["content"][0]["text"])

    # 2. Web Dashboard Telemetry Call
    url = f"{trinity_dashboard_server}/api/telemetry"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        dash_payload = json.loads(resp.read().decode("utf-8"))

    # 3. Console Status Execution
    console = AERInteractiveConsole(node_id="0x70997970C51812dc3A010C7d01b50e0d17dc79C8", enable_sound=False)
    captured = io.StringIO()
    with patch("sys.stdout", new=captured):
        res = console.execute_command("status")
        assert res is True
        console_out = captured.getvalue()

    # 4. Cross-Validation of Core State
    assert "AMD fTPM 2.0" in console_out or "fTPM" in console_out
    assert mcp_payload["status"] == "ONLINE"
    assert dash_payload["daemon"]["status"] == "ONLINE"
    assert dash_payload["mesh"]["total_nodes"] == 10000
    assert "silicon_anchor" in mcp_payload
    assert mcp_payload["onchain_arbitrum_sepolia"]["dispute_verifier_gas"] == dash_payload["onchain"]["dispute_verifier_gas"]


def test_trinity_operator_actions(trinity_dashboard_server):
    """
    Verify operator actions across Dashboard POST, MCP tools, and TTY Console commands:
    - Priority Netting execution
    - Z3 Formal Invariant verification
    - Bounty task discovery
    """
    # 1. Dashboard POST /api/action/netting
    req_net = urllib.request.Request(
        f"{trinity_dashboard_server}/api/action/netting",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_net, timeout=2.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "OK"
        assert "Priority Netting executed" in data["message"]

    # 2. MCP Trigger Netting Tool
    mcp = AERProductionMCPServer()
    mcp_net_call = {
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "aer_trigger_netting",
            "arguments": {"max_cycles": 5}
        }
    }
    net_resp = mcp.handle_jsonrpc(mcp_net_call)
    net_content = json.loads(net_resp["result"]["content"][0]["text"])
    assert net_content["execution_status"] == "CONVERGED"
    assert net_content["cycles_resolved"] == 3
    assert net_content["credit_b_cancelled"] == 4500

    # 3. Console Command Line Execution
    console = AERInteractiveConsole(node_id="0x70997970C51812dc3A010C7d01b50e0d17dc79C8", enable_sound=False)
    captured = io.StringIO()
    with patch("sys.stdout", new=captured):
        ok = console.execute_command("netting")
        assert ok is True
        out = captured.getvalue()
        assert "Priority Circular Debt Netting" in out
        assert "4,500 Credit B" in out


def test_trinity_bounty_and_task_lifecycle():
    """
    Cross-verify Bounty posting and task lifecycle between Console, MCP, and Sandbox Engine.
    """
    mcp = AERProductionMCPServer()
    post_call = {
        "jsonrpc": "2.0",
        "id": 103,
        "method": "tools/call",
        "params": {
            "name": "aer_post_bounty",
            "arguments": {
                "task_type": "TRINITY_E2E_VOXEL_SOLVE",
                "reward_credit_b": 2400,
                "description": "Cross-interface integration benchmark test"
            }
        }
    }
    post_res = mcp.handle_jsonrpc(post_call)
    post_data = json.loads(post_res["result"]["content"][0]["text"])
    task_id = post_data["task_id"]
    assert task_id.startswith("task_")
    assert post_data["reward_credit_b"] == 2400

    # Execute task via MCP
    exec_call = {
        "jsonrpc": "2.0",
        "id": 104,
        "method": "tools/call",
        "params": {
            "name": "aer_execute_task",
            "arguments": {
                "task_id": task_id,
                "payload_code": "fn trinity_solve() -> i32 { return 777; }"
            }
        }
    }
    exec_res = mcp.handle_jsonrpc(exec_call)
    exec_data = json.loads(exec_res["result"]["content"][0]["text"])
    assert exec_data["success"] is True
    assert exec_data["manifest_type"] == "ExecutionReceipt"

    # Console lists bounties
    console = AERInteractiveConsole(node_id="0x70997970C51812dc3A010C7d01b50e0d17dc79C8", enable_sound=False)
    captured = io.StringIO()
    with patch("sys.stdout", new=captured):
        ok = console.execute_command("bounty list")
        assert ok is True
        out = captured.getvalue()
        assert "AER DISTRIBUTED COMPUTATIONAL BOUNTIES" in out


def test_trinity_z3_verification_alignment(trinity_dashboard_server):
    """
    Verify formal Z3 invariant proofs are uniformly accessible via:
    - Dashboard POST /api/action/z3
    - MCP Tool aer_verify_invariants
    - Console 'z3-verify' command
    """
    # 1. Dashboard POST /api/action/z3
    req_z3 = urllib.request.Request(
        f"{trinity_dashboard_server}/api/action/z3",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_z3, timeout=2.0) as resp:
        assert resp.status == 200
        dash_z3 = json.loads(resp.read().decode("utf-8"))
        assert "PROVEN (100%)" in dash_z3["message"]

    # 2. MCP aer_verify_invariants
    mcp = AERProductionMCPServer()
    z3_call = {
        "jsonrpc": "2.0",
        "id": 105,
        "method": "tools/call",
        "params": {
            "name": "aer_verify_invariants",
            "arguments": {}
        }
    }
    z3_res = mcp.handle_jsonrpc(z3_call)
    z3_text = z3_res["result"]["content"][0]["text"]
    assert "ALL_INVARIANTS_PROVEN" in z3_text
    assert "Asset Orthogonality" in z3_text
    assert "Netting Deadlock Absence" in z3_text
    assert "Capital Conservation" in z3_text

    # 3. Console z3-verify command
    console = AERInteractiveConsole(node_id="0x70997970C51812dc3A010C7d01b50e0d17dc79C8", enable_sound=False)
    captured = io.StringIO()
    with patch("sys.stdout", new=captured):
        ok = console.execute_command("z3-verify")
        assert ok is True
        out = captured.getvalue()
        assert "Z3 SMT Solver on 3 Core Mathematical Invariants" in out
        assert "Asset Orthogonality" in out
