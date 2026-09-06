"""
AER Simulation Master Test Suite (Phase 4)
Rigorous unit test verification across all 6 economics and distributed systems simulations.
"""

import os
import sys
from typing import Dict, Any

# Ensure project root and src are in sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src"))
sys.path.insert(0, _PROJECT_ROOT)

sys.stdout.reconfigure(encoding="utf-8")

from simulation.simulate_phase_transition import run_phase_transition_simulation
from simulation.simulate_offline_netting import run_offline_netting_simulation
from simulation.simulate_supernova import run_supernova_simulation
from simulation.simulate_macro_arbitrage import run_macro_arbitrage_simulation
from simulation.simulate_black_market import run_black_market_simulation
from simulation.simulate_hardware_handover import run_hardware_handover_simulation


def test_phase_transition_avalanche() -> bool:
    """Test 1: Verify phase transition avalanche vs traditional linear slashing."""
    print("\n[Test 1] Testing Trust Phase Transition Avalanche...")
    res = run_phase_transition_simulation(total_steps=100, defect_ratio=0.08)
    assert res["trad_capital_growth_percent"] > 0, "Whale capital should grow under linear slashing"
    assert res["aer_boycotted"] is True, "AER node must be quarantined upon crossing Omega_c"
    assert res["aer_loss_percent"] > 90.0, "AER avalanche must destroy >90% of reputation"
    assert res["hysteresis_recovery_work_required"] > 900, "High hysteresis recovery barrier required"
    print("  [+] Phase transition avalanche and hysteresis barrier verified.")
    return True


def test_offline_netting_waterfall() -> bool:
    """Test 2: Verify 200 kWh offline charging and automated priority netting."""
    print("\n[Test 2] Testing Offline Multi-Charging & Priority Netting Waterfall...")
    res = run_offline_netting_simulation()
    assert res["total_energy_kwh"] == 200.0, "Energy delivered must equal 200 kWh"
    assert res["outstanding_debt"] == 0, "All offline IOUs must be retired"
    assert res["all_ious_cleared"] is True, "All station notes must be marked cleared"
    assert res["net_payout"] == 685, "Net worker payout must match 685 Credit B"
    print("  [+] Offline multi-charging, IOU ingestion, and netting waterfall verified.")
    return True


def test_guild_supernova_bulkhead() -> bool:
    """Test 3: Verify guild master supernova collapse and bulkhead worker protection."""
    print("\n[Test 3] Testing Guild Supernova & Bulkhead Containment...")
    res = run_supernova_simulation(worker_count=20, tasks_per_worker=10)
    assert res["master_collateral_slashed"] == 50_000, "Master collateral must be forfeited"
    assert res["worker_capital_loss"] == 0, "Innocent worker assets must suffer 0 loss"
    assert res["worker_loss_ratio"] == 0.0, "Worker loss ratio must be exactly 0.0"
    assert res["blast_radius_contained"] is True, "Blast radius must be contained by bulkhead"
    print("  [+] Supernova dissolution and bulkhead asset isolation verified.")
    return True


def test_macro_arbitrage_and_peg() -> bool:
    """Test 4: Verify Philanthropist's Paradox, mutual credit bypass, and energy peg."""
    print("\n[Test 4] Testing Macro Arbitrage, Cartel Monopoly Paradox & Energy Peg...")
    res = run_macro_arbitrage_simulation()
    assert res["cartel_credit_a_gained"] == 0, "Cartel must gain 0 Credit A (Asset Orthogonality)"
    assert res["mutual_credit_unlocked_per_node"] > 0, "Mutual credit line must unlock for honest nodes"
    assert res["peg_stability_pass"] is True, "1 Credit B must anchor to 0.1 kWh energy within 0.001 USD"
    print("  [+] Philanthropist's paradox and self-anchoring thermodynamic peg verified.")
    return True


def test_black_market_loot() -> bool:
    """Test 5: Verify 1,000 node serverless P2P double auction and digital loot acquisition."""
    print("\n[Test 5] Testing Serverless P2P Black Market & Digital Loot...")
    res = run_black_market_simulation(node_count=1000)
    assert res["total_nodes"] == 1000, "Must simulate 1,000 swarm nodes"
    assert res["matches_executed"] >= 2, "Orders must execute across GPU and MCP topics"
    assert res["digital_loot_acquired"] is True, "Autonomous digital loot acquisition must succeed"
    print("  [+] Serverless P2P double auction and digital loot acquisition verified.")
    return True


def test_hardware_handover_and_recovery() -> bool:
    """Test 6: Verify dual cross-signing handover and 7-day quarantine disaster recovery."""
    print("\n[Test 6] Testing Hardware Handover & 7-Day Quarantine Disaster Recovery...")
    res = run_hardware_handover_simulation()
    assert res["graceful_handover_success"] is True, "Graceful hardware swap must succeed instantly"
    assert res["premature_theft_blocked"] is True, "Premature recovery before 7 days must be blocked"
    assert res["capital_immortality_verified"] is True, "Account capital must be preserved 100%"
    print("  [+] Dual cross-signing handover and 7-day disaster recovery verified.")
    return True


def run_master_simulation_test_suite() -> bool:
    """Executes all 6 simulation verification tests."""
    print("=" * 68)
    print("AER Simulation Suite: Master Economics & P2P Verification (Phase 4)")
    print("=" * 68)

    tests = [
        test_phase_transition_avalanche,
        test_offline_netting_waterfall,
        test_guild_supernova_bulkhead,
        test_macro_arbitrage_and_peg,
        test_black_market_loot,
        test_hardware_handover_and_recovery
    ]

    for test_fn in tests:
        success = test_fn()
        if not success:
            print(f"[-] Test failed: {test_fn.__name__}")
            return False

    print("\n" + "-" * 68)
    print("STATUS: ALL 6 AER SIMULATION ENGINES VERIFIED (100%)")
    print("=" * 68 + "\n")
    return True


if __name__ == "__main__":
    _all_passed = run_master_simulation_test_suite()
    if not _all_passed:
        sys.exit(1)
    sys.exit(0)
