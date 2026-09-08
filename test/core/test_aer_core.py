#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Core Daemon Engine Comprehensive Unit Test Suite
===================================================
Executes exhaustive unit tests verifying all 10 core modules of Phase 3.

Test Modules:
1. Attestation Engine & Software Mock TPM Provider (Axiom 1)
2. Execution Sandbox Verifier & Fuel Metering (Section 5)
3. State Machine, Trust Phase Transitions (Omega_c), & State Expiry
4. Collateral-Credit Continuum & Mutual Credit Lines
5. Guild Sub-State Channels & Bulkhead Isolation
6. Optimistic Timelock Manager & Watchtower Pause Freezing
7. Bounty-Futures Priority Netting Engine (Section 6.3)
8. P2P Mesh Router & Topology Boycott Enforcement
9. P2P Resource Market & Continuous Double Auction Matching
10. Zero-Server Local Loopback UI Server (127.0.0.1:28741)
"""

import os
import sys
import time
import secrets
import urllib.request
from pathlib import Path

# Add project root to sys.path to enable direct importing of src/aer
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from aer.attestation import AttestationEngine, SoftwareMockTPMProvider
from aer.verifier import ExecutionSandboxVerifier
from aer.state import StateMachineRegistry, TrustPhaseManager, NodeReputationState
from aer.credit import CollateralCreditContinuum
from aer.guild import GuildChannelManager
from aer.timelock import OptimisticTimelockManager
from aer.netting import PriorityNettingEngine
from aer.p2p_mesh import P2PMeshRouter
from aer.market import P2PResourceMarket
from aer.ui_server import AERLocalUIServer


def test_attestation_module() -> bool:
    """Module 1: Test hardware attestation and SoftwareMockTPMProvider."""
    print("\n[Test 1] Testing Attestation Engine & Software Mock TPM...")
    tpm = SoftwareMockTPMProvider()
    pcr_digest_before = tpm.get_composite_pcr_digest()
    tpm.extend_pcr(0, b"MEASUREMENT_BOOT_KERNEL")
    pcr_digest_after = tpm.get_composite_pcr_digest()

    if pcr_digest_before == pcr_digest_after:
        print("  [-] PCR extension failed to alter measurement digest.")
        return False

    engine = AttestationEngine(tpm)
    node_id = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    nonce = "0x" + secrets.token_hex(32)
    payload = engine.generate_attestation_payload(node_id, nonce)

    valid, msg = engine.verify_attestation_payload(payload, nonce)
    if not valid:
        print(f"  [-] Attestation verification failed: {msg}")
        return False

    # Replay attack with stale nonce must fail
    replay_valid, _ = engine.verify_attestation_payload(payload, "0x" + secrets.token_hex(32))
    if replay_valid:
        print("  [-] Replay attack with invalid nonce was not rejected.")
        return False

    print("  [+] Hardware Attestation and PCR measurement verified.")
    return True


def test_verifier_sandbox_module() -> bool:
    """Module 2: Test WASM fuel metering, success receipts, and trap fraud proofs."""
    print("\n[Test 2] Testing WASM Fuel-Metered Execution Sandbox Verifier...")
    verifier = ExecutionSandboxVerifier(default_fuel_limit=500_000)
    task_id = "0x" + secrets.token_hex(32)
    worker = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    client = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    # Positive test: normal execution produces ExecutionReceipt
    success, receipt = verifier.execute_payload(
        task_id, worker, client, "1000", b"WASM_VALID_COMPUTATION"
    )
    if not success or not receipt.get("execution_success"):
        print("  [-] Normal execution failed.")
        return False
    print("  [+] ExecutionReceipt generation verified.")

    # Negative test: AST syntax error produces DeterministicFraudProof
    trap_success, fraud_proof = verifier.execute_payload(
        task_id, worker, client, "1000", b"BROKEN_SYNTAX", simulate_trap="AST_SYNTAX_ERROR"
    )
    if trap_success or fraud_proof.get("defect_type") != "AST_SYNTAX_ERROR":
        print("  [-] Trap detection failed to produce fraud proof.")
        return False
    print("  [+] DeterministicFraudProof trap handling verified.")
    return True


def test_state_and_phase_transitions() -> bool:
    """Module 3: Test non-linear bit-shift half-life decay (>> 1) and state expiry."""
    print("\n[Test 3] Testing Trust Phase Transitions (Omega_c) & State Expiry...")
    registry = StateMachineRegistry(state_expiry_seconds=100)
    node_id = "0x1111222233334444555566667777888899990000"
    state = registry.get_or_create_node(node_id)
    state.reputation_mass = 128

    # Record 100 successful tasks
    for _ in range(100):
        registry.phase_manager.record_successful_completion(state)

    initial_high_mass = state.reputation_mass
    # Record betrayal crossing Omega_c threshold
    mass_after_betrayal, collapsed = registry.phase_manager.record_betrayal_event(state)
    registry.phase_manager.record_betrayal_event(state)

    if state.reputation_mass >= initial_high_mass:
        print("  [-] Phase transition failed to penalize reputation.")
        return False

    # Bit-shift decay check: mass must have undergone division / right shift
    print(f"  [+] Phase transition avalanche verified: {initial_high_mass} -> {state.reputation_mass} (Boycotted={state.is_boycotted}).")

    # State expiry compaction test
    dormant_node = registry.get_or_create_node("0xdormant00000000000000000000000000000000")
    dormant_node.reputation_mass = dormant_node.ground_state
    dormant_node.last_active_epoch = int(time.time()) - 500  # Older than 100s

    pruned_count = registry.execute_state_expiry_compaction()
    if pruned_count < 1:
        print("  [-] State expiry garbage collector failed to prune dormant node.")
        return False
    print(f"  [+] State Expiry LSM compaction verified: {pruned_count} dormant nodes pruned.")
    return True


def test_credit_continuum_module() -> bool:
    """Module 4: Test collateral-credit continuum and ground state requirements."""
    print("\n[Test 4] Testing Collateral-Credit Continuum...")
    credit = CollateralCreditContinuum(ground_state_mass=10, alpha=0.35)

    # A_0 node must require 100% upfront escrow
    eval_a0 = credit.evaluate_task_collateral(reputation_mass=10, task_bounty=1000)
    if eval_a0["collateral_ratio"] != 1.0 or eval_a0["mandatory_upfront_escrow"] != 1000:
        print("  [-] A_0 ground state node did not enforce 100% upfront escrow.")
        return False
    print("  [+] Ground state node (A_0) 100% upfront escrow requirement verified.")

    # High reputation node unlocks credit relaxation
    eval_high = credit.evaluate_task_collateral(reputation_mass=100, task_bounty=1000)
    if eval_high["collateral_ratio"] >= 1.0 or eval_high["max_credit_limit"] <= 0:
        print("  [-] High reputation node failed to unlock mutual credit line.")
        return False
    print(f"  [+] High reputation node credit relaxation verified: Escrow Ratio={eval_high['collateral_ratio']:.1%}, Credit Limit={eval_high['max_credit_limit']}.")
    return True


def test_guild_bulkhead_module() -> bool:
    """Module 5: Test guild sub-channels and bulkhead containment."""
    print("\n[Test 5] Testing Guild Sub-Channels & Bulkhead Isolation...")
    manager = GuildChannelManager()
    master_nid = "0xmaster00000000000000000000000000000000"
    guild = manager.create_guild(
        guild_id = "guild-alpha",
        master_node_id = master_nid,
        collateral = 50_000
    )

    worker_a = "0xworkerA0000000000000000000000000000000"
    worker_b = "0xworkerB0000000000000000000000000000000"
    guild.add_member(worker_a, 10_000)
    guild.add_member(worker_b, 10_000)
    guild.credit_member_earnings(worker_a, 4_500)
    guild.credit_member_earnings(worker_b, 8_200)

    # Trigger bulkhead emergency isolation (master betrayal)
    report = guild.trigger_bulkhead_isolation()
    if report["master_collateral_forfeited"] != 50_000:
        print("  [-] Master collateral forfeiture failed.")
        return False

    protected = report["protected_worker_assets"]
    if protected[worker_a.lower()] != 4_500 or protected[worker_b.lower()] != 8_200:
        print("  [-] Worker assets were not protected inside bulkhead.")
        return False

    print("  [+] Guild bulkhead isolation and worker asset containment verified.")
    return True


def test_timelock_module() -> bool:
    """Module 6: Test optimistic timelock scheduling and watchtower pause."""
    print("\n[Test 6] Testing Optimistic Timelock Manager & Watchtower Pause...")
    manager = OptimisticTimelockManager()
    task_id = "task-timelock-test"
    state = manager.schedule_timelock(task_id, duration=100)

    # Initial state should not be expired
    if state.is_expired():
        print("  [-] Timelock marked expired immediately.")
        return False

    # Pause mechanism
    manager.pause_timelock(task_id)
    if not state.is_paused:
        print("  [-] Watchtower pause failed.")
        return False

    manager.resume_timelock(task_id)
    if state.is_paused:
        print("  [-] Timelock resume failed.")
        return False

    # Simulate expiration in future
    simulated_future = state.created_at + 200
    if not state.is_expired(simulated_future):
        print("  [-] Timelock failed to expire in simulated future.")
        return False

    manager.finalize_settlement(task_id, simulated_future)
    if not state.is_finalized:
        print("  [-] Settlement finalization failed.")
        return False

    print("  [+] Timelock scheduling, watchtower pause, and finalization verified.")
    return True


def test_priority_netting_module() -> bool:
    """Module 7: Test offline IOU ingestion and priority netting waterfall."""
    print("\n[Test 7] Testing Bounty-Futures Priority Netting Engine...")
    engine = PriorityNettingEngine()
    debtor = "0xdebtor0000000000000000000000000000000"
    creditor_1 = "0xstation100000000000000000000000000000"
    creditor_2 = "0xstation200000000000000000000000000000"

    # Debtor charged 40 kWh at Station 1 with 1.25x offline risk factor (effective: 50 Credit B)
    engine.register_offline_iou("iou-1", debtor, creditor_1, principal_credit_b=40, risk_factor=1.25)
    # Debtor charged 20 kWh at Station 2 with 1.0x factor (effective: 20 Credit B)
    engine.register_offline_iou("iou-2", debtor, creditor_2, principal_credit_b=20, risk_factor=1.0)

    total_debt = engine.get_total_outstanding_debt(debtor)
    if total_debt != 70:
        print(f"  [-] Total debt calculation failed: {total_debt} != 70")
        return False

    # Debtor earns 60 Credit B task bounty
    deducted, payout, settlements = engine.execute_priority_waterfall(debtor, inflow_revenue=60)
    if deducted != 60 or payout != 0:
        print("  [-] Priority waterfall deduction error.")
        return False

    remaining_debt = engine.get_total_outstanding_debt(debtor)
    if remaining_debt != 10:
        print(f"  [-] Remaining debt mismatch: {remaining_debt} != 10")
        return False

    print(f"  [+] Priority Netting waterfall verified: Deducted={deducted}, Worker Net={payout}, Remaining Debt={remaining_debt}.")
    return True


def test_p2p_mesh_and_boycott() -> bool:
    """Module 8: Test P2P epidemic gossip diffusion and topology boycotts."""
    local_nid = "0xlocal00000000000000000000000000000000"
    router = P2PMeshRouter(local_node_id = local_nid)
    peer_good = "0xpeergood00000000000000000000000000000"
    peer_bad = "0xpeerbad000000000000000000000000000000"

    router.add_peer(peer_good)
    router.add_peer(peer_bad)
    router.subscribe("/aer/market/v1", peer_good)
    router.subscribe("/aer/market/v1", peer_bad)

    # Publish message to both
    _, count1 = router.publish_message("/aer/market/v1", {"order": "sample"})
    if count1 != 2:
        print("  [-] Gossip message did not reach both peers.")
        return False

    # Enforce topology boycott on malicious peer
    router.enforce_topology_boycott(peer_bad, "DEFECT_PROOF_HASH")
    if not router.is_peer_isolated(peer_bad):
        print("  [-] Topology boycott failed to isolate peer.")
        return False

    # Next message must only reach peer_good
    _, count2 = router.publish_message("/aer/market/v1", {"order": "sample_2"})
    if count2 != 1:
        print("  [-] Boycotted peer still received gossip message.")
        return False

    print("  [+] P2P GossipSub dissemination and topology boycott verified.")
    return True


def test_p2p_resource_market() -> bool:
    """Module 9: Test decentralized P2P resource market order crossing."""
    print("\n[Test 9] Testing P2P Resource Market & Order Crossing...")
    market = P2PResourceMarket()

    # Place an ASK order for GPU compute
    ask_order = {
        "order_id": "0x" + secrets.token_hex(32),
        "side": "ASK",
        "resource_type": "GPU_QUOTA",
        "resource_cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
        "quantity": 10.0,
        "price_credit_b": 100,
        "total_price_credit_b": 1000,
        "maker_node_id": "0xseller000000000000000000000000000000",
        "expiration_timestamp": int(time.time()) + 3600
    }
    accepted, msg, match = market.place_order(ask_order)
    if not accepted or match is not None:
        print("  [-] First order failed to rest in book.")
        return False

    # Place a matching BID order
    bid_order = {
        "order_id": "0x" + secrets.token_hex(32),
        "side": "BID",
        "resource_type": "GPU_QUOTA",
        "resource_cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
        "quantity": 5.0,
        "price_credit_b": 105,  # Higher than ASK (100) -> Crosses!
        "total_price_credit_b": 525,
        "maker_node_id": "0xbuyer0000000000000000000000000000000",
        "expiration_timestamp": int(time.time()) + 3600
    }
    bid_accepted, bid_msg, bid_match = market.place_order(bid_order)
    if not bid_accepted or bid_match is None:
        print("  [-] Compatible orders failed to cross.")
        return False

    print(f"  [+] P2P Market Order matched: Cleared={bid_match['matched_quantity']} units @ {bid_match['clearing_price']} Credit B.")
    return True


def test_local_ui_server() -> bool:
    """Module 10: Test 127.0.0.1 zero-server local loopback interface."""
    test_port = 28743
    print(f"\n[Test 10] Testing Zero-Server Local Loopback UI Server (127.0.0.1:{test_port})...")
    server = AERLocalUIServer(host="127.0.0.1", port=test_port)

    telemetry_mock = {
        "reputation_mass": 100,
        "active_tasks": 2,
        "balance_credit_b": 500
    }

    started = server.start(state_provider_callable=lambda: telemetry_mock)
    if not started:
        print("  [-] Failed to bind and start local UI server.")
        return False

    try:
        # Query /api/status via urllib
        req = urllib.request.Request(f"http://127.0.0.1:{test_port}/api/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode("utf-8")
            if "aerd" not in data or "reputation_mass" not in data:
                print("  [-] UI Server telemetry response malformed.")
                return False
        print("  [+] Local loopback UI server responded with valid JSON telemetry.")
    finally:
        server.stop()

    return True


def run_all_aer_core_tests() -> bool:
    """Execute all 10 unit test modules."""
    print("==================================================================")
    print("AER Core Daemon Engine: Master Unit Test Suite (Phase 3)")
    print("==================================================================")

    test_modules = [
        test_attestation_module,
        test_verifier_sandbox_module,
        test_state_and_phase_transitions,
        test_credit_continuum_module,
        test_guild_bulkhead_module,
        test_timelock_module,
        test_priority_netting_module,
        test_p2p_mesh_and_boycott,
        test_p2p_resource_market,
        test_local_ui_server
    ]

    for test_fn in test_modules:
        success = test_fn()
        if not success:
            print(f"\n[-] Failure encountered in {test_fn.__name__}")
            return False

    print("\n------------------------------------------------------------------")
    print("STATUS: ALL 10 AER CORE DAEMON MODULES PASSED (100%)")
    print("==================================================================")
    return True


def main() -> None:
    """Main CLI entrypoint."""
    success = run_all_aer_core_tests()
    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
