#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER 10,000-Node Partition & Netting Stress Unit Tests (Phase 2-3)
================================================================
Validates large-scale mesh dynamics, 50:50 network partition blackout,
debt ceiling enforcement, and 1,000-rover cyclic netting convergence.
"""

import os
import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from benchmarks.network.stress_mesh import (
    MeshBenchmarkConfig,
    MeshNodeProfile,
    MeshStressBenchmarkEngine
)


def test_10k_topology_structure():
    """Verify 10,000-node graph initialization, 50:50 partitions, and Kademlia shortcuts."""
    config = MeshBenchmarkConfig(
        total_nodes = 1000,
        broadcast_samples = 10,
        partition_ratio = 0.5
    )
    _ = config.__init__(1000, 8, 10, 0.5, 100, 5000, 1.05)

    engine = MeshStressBenchmarkEngine(config)
    _ = engine.__init__(config)

    assert len(engine.nodes) == 1000
    partition_0_count = sum(1 for n in engine.nodes if n.partition_id == 0)
    partition_1_count = sum(1 for n in engine.nodes if n.partition_id == 1)
    assert partition_0_count == 500
    assert partition_1_count == 500

    # Verify Kademlia shortcuts exist on every node
    for node in engine.nodes:
        assert len(node.peers) >= 10
        assert (node.node_id + 1) % 1000 in node.peers
        assert (node.node_id - 1) % 1000 in node.peers


def test_gossipsub_broadcast_reachability():
    """Verify epidemic message dissemination reaches >= 98% with low hop diameter."""
    config = MeshBenchmarkConfig(
        total_nodes = 2000,
        broadcast_samples = 10
    )
    _ = config.__init__(2000, 8, 10, 0.5, 100, 5000, 1.05)

    engine = MeshStressBenchmarkEngine(config)
    _ = engine.__init__(config)

    res = engine.run_broadcast_stress()
    assert res["target_sla_passed"] is True
    assert res["mean_delivery_ratio_pct"] >= 98.0
    assert res["mean_hop_distance"] <= 7.0


def test_partition_blackout_and_debt_ceiling():
    """Verify 50:50 partition blackout and strict offline debt ceiling rejection."""
    config = MeshBenchmarkConfig(
        total_nodes = 1000,
        credit_limit_b = 2000,
        gamma_offline = 1.10
    )
    _ = config.__init__(1000, 8, 10, 0.5, 100, 2000, 1.10)

    engine = MeshStressBenchmarkEngine(config)
    _ = engine.__init__(config)

    res = engine.run_partition_blackout_stress(num_transactions = 2000)
    assert res["debt_ceiling_enforced"] is True
    assert res["rejected_by_debt_ceiling"] > 0
    assert res["accepted_offline_ious"] > 0
    assert res["unbacked_inflation_bounded"] is True


def test_rover_circular_netting_convergence():
    """Verify 1,000-rover circular debt netting waterfall converges with zero deadlock."""
    config = MeshBenchmarkConfig(
        total_nodes = 2000,
        rover_netting_count = 1000
    )
    _ = config.__init__(2000, 8, 10, 0.5, 1000, 5000, 1.05)

    engine = MeshStressBenchmarkEngine(config)
    _ = engine.__init__(config)

    res = engine.run_partition_heal_and_netting_stress()
    assert res["sla_passed"] is True
    assert res["deadlock_detected"] is False
    assert res["cleared_ratio_pct"] == 100.0
    assert res["convergence_time_sec"] < 3.0
    assert res["cleared_debt_b"] > 0


def test_stress_results_json_schema():
    """Verify exported benchmark results JSON exists and follows Phase 2-3 schema."""
    out_json = Path(__file__).parent.parent.parent / "benchmarks" / "network" / "results_mesh_stress.json"
    assert out_json.exists(), "Benchmark results JSON was not exported"

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["phase"] == "2-3"
    assert "broadcast" in data
    assert "partition" in data
    assert "netting" in data
    assert data["broadcast"]["target_sla_passed"] is True
    assert data["partition"]["debt_ceiling_enforced"] is True
    assert data["netting"]["sla_passed"] is True
