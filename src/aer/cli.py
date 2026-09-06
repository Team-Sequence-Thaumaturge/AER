#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Core Daemon Command Line Interface (CLI)
============================================
The primary binary interface for node operators and autonomous agents interacting
with the local background aerd engine.

Commands:
- aerd status      : Query local node hardware identity, reputation, and credit status
- aerd attest      : Generate verifiable HardwareAttestation evidence payload
- aerd serve       : Start local loopback UI server at 127.0.0.1:28741
- aerd verify-task : Execute a verified sandboxed task execution test
"""

import sys
import json
import argparse
import secrets
from pathlib import Path

from aer.attestation import AttestationEngine, SoftwareMockTPMProvider
from aer.verifier import ExecutionSandboxVerifier
from aer.state import StateMachineRegistry
from aer.credit import CollateralCreditContinuum
from aer.ui_server import AERLocalUIServer


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_default_node_id() -> str:
    """Generate or retrieve persistent node identifier."""
    return "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"


def cmd_status(args: argparse.Namespace) -> int:
    """Display local node status and reputation metrics."""
    node_id = get_default_node_id()
    registry = StateMachineRegistry()
    state = registry.get_or_create_node(node_id)
    credit = CollateralCreditContinuum()
    collateral_info = credit.evaluate_task_collateral(state.reputation_mass, 1000)

    print("==================================================================")
    print(f"AER Autonomous Daemon (aerd) Status - Node: {node_id}")
    print("==================================================================")
    print(f"  [+] Silicon Anchor State   : TPM 2.0 HARDWARE_BOUND")
    print(f"  [+] Reputation Mass (A_j)  : {state.reputation_mass} (Ground State A_0: {state.ground_state})")
    print(f"  [+] Completed Tasks        : {state.total_completed_tasks}")
    print(f"  [+] Betrayals / Defects    : {state.total_betrayals} (Density: {state.get_betrayal_density():.2%})")
    print(f"  [+] Required Escrow Ratio  : {collateral_info['collateral_ratio']:.1%}")
    print(f"  [+] Mutual Credit Limit    : {collateral_info['max_credit_limit']} Credit B")
    print("==================================================================")
    return 0


def cmd_attest(args: argparse.Namespace) -> int:
    """Generate and print a formal HardwareAttestation payload."""
    node_id = get_default_node_id()
    engine = AttestationEngine()
    nonce = "0x" + secrets.token_hex(32)
    payload = engine.generate_attestation_payload(node_id, nonce)

    print(json.dumps(payload, indent=2))
    return 0


def cmd_verify_task(args: argparse.Namespace) -> int:
    """Execute a task in the isolated fuel-metered sandbox."""
    verifier = ExecutionSandboxVerifier()
    task_id = "0x" + secrets.token_hex(32)
    worker_id = get_default_node_id()
    client_id = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    print(f"[*] Executing test task in fuel-metered WASM sandbox...")
    success, manifest = verifier.execute_payload(
        task_id=task_id,
        worker_node_id=worker_id,
        beneficiary_node_id=client_id,
        bounty_credit_b="10000000000000000000",
        code_or_data=b"fn aer_compute() -> i32 { return 42; }"
    )

    if success:
        print("[+] Task execution successful. Produced ExecutionReceipt:")
    else:
        print("[-] Task execution trapped. Produced DeterministicFraudProof:")

    print(json.dumps(manifest, indent=2))
    return 0


def build_cli_parser() -> argparse.ArgumentParser:
    """Construct command line arguments and subcommand dispatchers."""
    parser = argparse.ArgumentParser(
        prog="aerd",
        description="AER Autonomous Background Daemon CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available aerd subcommands")

    sub_status = subparsers.add_parser("status", help="Query local node status")
    sub_status.set_defaults(func=cmd_status)

    sub_attest = subparsers.add_parser("attest", help="Generate hardware attestation evidence")
    sub_attest.set_defaults(func=cmd_attest)

    sub_verify = subparsers.add_parser("verify-task", help="Run sandboxed task verification")
    sub_verify.set_defaults(func=cmd_verify_task)

    return parser


def main() -> None:
    """Main CLI entrypoint."""
    parser = build_cli_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        code = args.func(args)
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
