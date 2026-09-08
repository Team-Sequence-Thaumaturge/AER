#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Production MCP Gateway Server Unit & Integration Tests (Phase 3-2)
=====================================================================
Validates:
1. Anthropic MCP stdio protocol handshake (initialize, notifications/initialized, ping)
2. 6 production tools declaration in tools/list
3. Tool invocation via tools/call (aer_get_telemetry, aer_verify_invariants, aer_post_bounty, aer_execute_task)
"""

import os
import sys
import json
import unittest
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aer.mcp_server import AERProductionMCPServer


class TestAERProductionMCPServer(unittest.TestCase):

    def setUp(self):
        self.server = AERProductionMCPServer()

    def test_01_tool_definitions(self):
        """Ensure all 6 production tools are declared with valid schemas."""
        tools = self.server.get_tool_definitions()
        self.assertEqual(len(tools), 6)
        names = {t["name"] for t in tools}
        expected = {
            "aer_get_telemetry",
            "aer_verify_invariants",
            "aer_trigger_netting",
            "aer_query_orderbook",
            "aer_post_bounty",
            "aer_execute_task"
        }
        self.assertEqual(names, expected)

    def test_02_jsonrpc_handshake(self):
        """Test initialize and ping methods."""
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.server.handle_jsonrpc(init_req)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "aer-production-mcp-gateway")

        ping_req = {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}
        ping_resp = self.server.handle_jsonrpc(ping_req)
        self.assertEqual(ping_resp["id"], 2)

    def test_03_telemetry_tool_call(self):
        """Test aer_get_telemetry tool execution."""
        req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "aer_get_telemetry", "arguments": {}}
        }
        resp = self.server.handle_jsonrpc(req)
        self.assertEqual(resp["id"], 10)
        self.assertNotIn("isError", resp["result"])
        text = resp["result"]["content"][0]["text"]
        self.assertIn("silicon_anchor", text)
        self.assertIn("onchain_arbitrum_sepolia", text)

    def test_04_verify_invariants_tool_call(self):
        """Test aer_verify_invariants tool execution."""
        req = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "aer_verify_invariants", "arguments": {}}
        }
        resp = self.server.handle_jsonrpc(req)
        self.assertEqual(resp["id"], 11)
        text = resp["result"]["content"][0]["text"]
        self.assertIn("ALL_INVARIANTS_PROVEN", text)
        self.assertIn("Asset Orthogonality", text)

    def test_05_bounty_and_execute_task_tool_call(self):
        """Test AI posting a bounty and subsequently executing it in the sandbox."""
        # 1. Post bounty
        post_req = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "aer_post_bounty",
                "arguments": {
                    "task_type": "OCTREE_AI_DECOMPRESSION",
                    "reward_credit_b": 750,
                    "description": "Decompress neural octree stream"
                }
            }
        }
        post_resp = self.server.handle_jsonrpc(post_req)
        post_data = json.loads(post_resp["result"]["content"][0]["text"])
        task_id = post_data["task_id"]
        self.assertTrue(task_id.startswith("task_"))

        # 2. Execute task
        exec_req = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "aer_execute_task",
                "arguments": {
                    "task_id": task_id,
                    "payload_code": "fn mcp_solve() -> i32 { return 42; }"
                }
            }
        }
        exec_resp = self.server.handle_jsonrpc(exec_req)
        exec_data = json.loads(exec_resp["result"]["content"][0]["text"])
        self.assertTrue(exec_data["success"])
        self.assertEqual(exec_data["manifest_type"], "ExecutionReceipt")

    def test_06_stdio_process_isolation(self):
        """Test real sub-process stdio communication."""
        proc = subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "src" / "aer" / "mcp_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        try:
            req = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "initialize", "params": {}}) + "\n"
            proc.stdin.write(req)
            proc.stdin.flush()
            line = proc.stdout.readline()
            data = json.loads(line)
            self.assertEqual(data["id"], 99)
            self.assertEqual(data["result"]["protocolVersion"], "2024-11-05")
        finally:
            if proc.stdin:
                proc.stdin.close()
            if proc.stdout:
                proc.stdout.close()
            proc.terminate()
            proc.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
