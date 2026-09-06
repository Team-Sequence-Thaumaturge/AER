#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER On-Chain EVM Gas & Deployment Unit Tests (Phase 2-2)
=======================================================
Validates gas profiling correctness, DisputeVerifier <= 200k gas bound,
Plumber immediate settlement economic delta, and deployment manifest generation.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "benchmarks", "onchain")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts")))

from bench_onchain_gas import EVMGasBenchmarkEngine
from deploy_testnet import run_deployment_pipeline


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_evm_gas_profiles_completeness() -> None:
    """Verify all 10 core smart contract methods possess gas profiles."""
    engine = EVMGasBenchmarkEngine()
    _ = engine.__init__()
    profiles = engine.evaluate_profiles()

    assert len(profiles) == 10
    methods = [p["method"] for p in profiles]
    assert "createTask" in methods
    assert "settleTaskDirect" in methods
    assert "settleTaskAfterTimelock" in methods
    assert "verify3DOctreeDispute" in methods
    assert "depositUSDT" in methods
    print("  [PASS] test_evm_gas_profiles_completeness")


def test_dispute_verifier_gas_ceiling() -> None:
    """Strictly verify that 3D Octree dispute bisection does not exceed 200,000 gas."""
    engine = EVMGasBenchmarkEngine()
    _ = engine.__init__()
    profiles = engine.evaluate_profiles()

    dispute_p = next(p for p in profiles if p["method"] == "verify3DOctreeDispute")
    assert dispute_p["gas_used"] <= 200000, f"Dispute gas {dispute_p['gas_used']} exceeded 200,000 limit!"
    assert dispute_p["gas_used"] == 142680
    print(f"  [PASS] test_dispute_verifier_gas_ceiling ({dispute_p['gas_used']:,} <= 200,000 Gas)")


def test_plumber_vs_timelock_gas_comparison() -> None:
    """Verify economic cost difference between instant payout and 24h timelock."""
    engine = EVMGasBenchmarkEngine()
    _ = engine.__init__()
    profiles = engine.evaluate_profiles()

    direct_p = next(p for p in profiles if p["method"] == "settleTaskDirect")
    timelock_p = next(p for p in profiles if p["method"] == "settleTaskAfterTimelock")

    # Direct settlement requires ecrecover (+2,540 gas) but eliminates 24h capital lockup
    delta_gas = direct_p["gas_used"] - timelock_p["gas_used"]
    assert delta_gas == 2540
    assert direct_p["arbitrum_cost_usd"] < 0.05
    print("  [PASS] test_plumber_vs_timelock_gas_comparison")


def test_l2_vs_l1_cost_savings() -> None:
    """Verify Arbitrum L2 delivers over 98% fee reduction compared to Ethereum L1."""
    engine = EVMGasBenchmarkEngine()
    _ = engine.__init__()
    profiles = engine.evaluate_profiles()

    for p in profiles:
        savings_ratio = 1.0 - (p["arbitrum_cost_usd"] / p["ethereum_l1_cost_usd"])
        assert savings_ratio >= 0.98, f"Savings on {p['method']} was {savings_ratio:.2%}"
    print("  [PASS] test_l2_vs_l1_cost_savings (> 98% savings on all methods)")


def test_deployment_dry_run_generation() -> None:
    """Verify deterministic testnet deployment pipeline outputs valid manifest."""
    manifest = run_deployment_pipeline(network_name="test_chain", is_dry_run=True)
    assert manifest["network"] == "test_chain"
    assert manifest["is_dry_run"] is True
    assert len(manifest["contracts"]) == 5

    for c_name, details in manifest["contracts"].items():
        assert details["address"].startswith("0x")
        assert len(details["address"]) == 42
        assert details["gas_used"] > 0
    print("  [PASS] test_deployment_dry_run_generation")


def run_all_onchain_profiling_tests() -> None:
    """Run all Phase 2-2 on-chain gas profiling tests."""
    print("==================================================================")
    print("AER On-Chain EVM Gas & Deployment Test Suite (Phase 2-2)")
    print("==================================================================")
    test_evm_gas_profiles_completeness()
    test_dispute_verifier_gas_ceiling()
    test_plumber_vs_timelock_gas_comparison()
    test_l2_vs_l1_cost_savings()
    test_deployment_dry_run_generation()
    print("==================================================================")
    print("ALL 5 ON-CHAIN GAS PROFILING TESTS PASSED 100%")
    print("==================================================================")


if __name__ == "__main__":
    run_all_onchain_profiling_tests()
