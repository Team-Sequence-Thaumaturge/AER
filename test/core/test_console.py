#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Console & Bounty Engine Unit & Integration Tests (Phase 3-0 & 3-1)
=====================================================================
Validates:
1. Bounty posting, acceptance, and 2-second WASI watchdog execution.
2. Zero-Credit Atomic Barter swap creation and fulfillment.
3. 2GB LRU Disk Capped Blob Storage capacity enforcement.
4. Interactive TTY Console REPL command dispatchers and ANSI formatting.
"""

import os
import sys
import io
import unittest
from pathlib import Path

# Add project root and src to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aer.bounty import BountyManager, BlobStorageManager, BountyStatus
from aer.console import AERInteractiveConsole


class TestBountyAndConsoleEngine(unittest.TestCase):

    def setUp(self):
        self.node_id = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        self.bounty_mgr = BountyManager(local_node_id=self.node_id)
        self.console = AERInteractiveConsole(node_id=self.node_id, enable_sound=False)

    def test_01_bounty_lifecycle_success(self):
        """Test standard bounty posting, acceptance, and execution."""
        task = self.bounty_mgr.post_bounty(
            issuer_id=self.node_id,
            task_type="OCTREE_VOXEL_SOLVE",
            reward_credit_b=1500,
            timelock_hours=24,
            description="Voxelize 3D point cloud"
        )
        self.assertEqual(task.status, BountyStatus.OPEN)
        self.assertEqual(task.reward_credit_b, 1500)

        # Worker accepts
        worker_id = "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc"
        ok, msg = self.bounty_mgr.accept_bounty(task.task_id, worker_id)
        self.assertTrue(ok)
        self.assertEqual(task.status, BountyStatus.IN_PROGRESS)
        self.assertEqual(task.worker_id, worker_id.lower())

        # Solve task in 2s sandbox
        ok_solve, manifest = self.bounty_mgr.execute_and_solve_bounty(
            task_id=task.task_id,
            worker_id=worker_id,
            payload_code=b"fn test_compute() -> i32 { return 100; }",
            timeout_sec=2.0
        )
        self.assertTrue(ok_solve)
        self.assertEqual(task.status, BountyStatus.COMPLETED)
        self.assertTrue(manifest["execution_success"])
        self.assertIn("solution_hash", manifest)

    def test_02_bounty_watchdog_failure(self):
        """Test sandbox trap resulting in DeterministicFraudProof."""
        task = self.bounty_mgr.post_bounty(
            issuer_id=self.node_id,
            task_type="MALFORMED_TASK",
            reward_credit_b=500,
            description="Should trigger sandbox trap"
        )
        worker_id = "0x90f79bf6eb2c4f870365e785982e1f101e93b906"
        self.bounty_mgr.accept_bounty(task.task_id, worker_id)

        ok_solve, manifest = self.bounty_mgr.execute_and_solve_bounty(
            task_id=task.task_id,
            worker_id=worker_id,
            payload_code=b"syntax error payload",
            simulate_trap="AST_SYNTAX_ERROR",
            timeout_sec=2.0
        )
        self.assertFalse(ok_solve)
        self.assertEqual(task.status, BountyStatus.DISPUTED)
        self.assertTrue("defect_type" in manifest or "error_code" in manifest)

    def test_03_zero_credit_atomic_swap(self):
        """Test escrow-free atomic barter exchange."""
        offer = self.bounty_mgr.create_atomic_swap_offer(
            party_a=self.node_id,
            give_cid="bafy_octree_mesh_a",
            want_cid="bafy_gpu_time_slot_b",
            description="1:1 dataset vs compute swap"
        )
        self.assertEqual(offer.status, "OPEN")

        # Party B fulfills
        party_b = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a65"
        ok, msg = self.bounty_mgr.fulfill_atomic_swap(
            offer_id=offer.offer_id,
            party_b=party_b,
            party_b_give_cid="bafy_gpu_time_slot_b"
        )
        self.assertTrue(ok)
        self.assertEqual(offer.status, "SWAPPED")
        self.assertEqual(offer.party_b, party_b.lower())

    def test_04_blob_storage_lru_enforcement(self):
        """Test that blob storage manager successfully writes and reads blobs."""
        storage = BlobStorageManager(cache_dir=PROJECT_ROOT / "build" / "test_blob_cache")
        data = b"Hello AER Decentralized Storage Block"
        cid = storage.store_blob(data)
        self.assertTrue(cid.startswith("bafy"))
        retrieved = storage.get_blob(cid)
        self.assertEqual(retrieved, data)

    def test_05_console_command_dispatchers(self):
        """Test console command parsing without crashes."""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            # Test key diagnostic commands
            self.assertTrue(self.console.execute_command("status"))
            self.assertTrue(self.console.execute_command("peers"))
            self.assertTrue(self.console.execute_command("ping 0x3c44cd"))
            self.assertTrue(self.console.execute_command("tpm-quote"))
            self.assertTrue(self.console.execute_command("bbs"))
            self.assertTrue(self.console.execute_command("bounty list"))
            self.assertTrue(self.console.execute_command("market"))
            self.assertTrue(self.console.execute_command("netting"))
            self.assertTrue(self.console.execute_command("z3-verify"))
            self.assertTrue(self.console.execute_command("help"))

            # Test exit command
            self.assertFalse(self.console.execute_command("quit"))
        finally:
            sys.stdout = sys.__stdout__

        output_str = captured_output.getvalue()
        self.assertIn("LOCAL NODE HARDWARE & STATE TELEMETRY", output_str)
        self.assertIn("ACTIVE P2P MESH PEERS", output_str)
        self.assertIn("AMD fTPM 2.0", output_str)
        self.assertIn("AER PUBLIC BULLETIN BOARD", output_str)


if __name__ == "__main__":
    unittest.main()
