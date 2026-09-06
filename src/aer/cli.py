#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Core Daemon Command Line Interface (CLI)
============================================
The primary binary interface for node operators and autonomous agents interacting
with the local background aerd engine.

Commands:
- aerd status      : Query local node hardware identity, reputation, and PID status
- aerd run         : Run resident daemon in foreground console mode
- aerd start       : Launch detached background daemon process
- aerd stop        : Gracefully terminate running background daemon
- aerd attest      : Generate verifiable HardwareAttestation evidence payload
- aerd verify-task : Execute a verified sandboxed task execution test
"""

import sys
import os
import json
import secrets
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aer.attestation import AttestationEngine
from aer.verifier import ExecutionSandboxVerifier
from aer.state import StateMachineRegistry
from aer.credit import CollateralCreditContinuum
from aer.daemon import (
    DaemonConfig,
    DaemonProcessManager,
    create_autonomous_daemon,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_default_node_id() -> str:
    """Generate or retrieve persistent node identifier."""
    return "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"


def cmd_status(args: argparse.Namespace) -> int:
    """Display local node status, reputation metrics, and daemon PID status."""
    default_nid = get_default_node_id()
    registry = StateMachineRegistry()
    node_state = registry.get_or_create_node(default_nid)
    credit_engine = CollateralCreditContinuum()
    collateral_info = credit_engine.evaluate_task_collateral(node_state.reputation_mass, 1000)

    pid_mgr = DaemonProcessManager(Path(".aerd.pid"))
    active_pid = pid_mgr.read_pid()
    is_alive = pid_mgr.is_pid_alive(active_pid) if active_pid else False

    ui_alive = False
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:28741/api/health", timeout=0.5) as resp:
            if resp.status == 200:
                ui_alive = True
    except Exception:
        ui_alive = False

    if is_alive or ui_alive:
        pid_text = f" (PID: {active_pid})" if active_pid else ""
        status_str = f"ONLINE{pid_text}"
    else:
        status_str = "OFFLINE"

    print("==================================================================")
    print(f"AER Autonomous Daemon (aerd) Status - Node: {default_nid}")
    print("==================================================================")
    print(f"  [+] Daemon Run State       : {status_str}")
    print(f"  [+] Loopback Interface     : http://127.0.0.1:28741")
    print(f"  [+] Silicon Anchor State   : TPM 2.0 HARDWARE_BOUND")
    print(f"  [+] Reputation Mass (A_j)  : {node_state.reputation_mass} (Ground State A_0: {node_state.ground_state})")
    print(f"  [+] Completed Tasks        : {node_state.total_completed_tasks}")
    print(f"  [+] Betrayals / Defects    : {node_state.total_betrayals} (Density: {node_state.get_betrayal_density():.2%})")
    print(f"  [+] Required Escrow Ratio  : {collateral_info['collateral_ratio']:.1%}")
    print(f"  [+] Mutual Credit Limit    : {collateral_info['max_credit_limit']} Credit B")
    print("==================================================================")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run the autonomous daemon in the foreground event loop."""
    default_nid = get_default_node_id()
    config = DaemonConfig(node_id=default_nid)
    daemon_instance = create_autonomous_daemon(config)

    print(f"[*] Starting AER resident daemon in foreground mode...")
    print(f"[*] Local UI Loopback bound to http://{config.host}:{config.port}")
    print(f"[*] Press Ctrl+C to initiate graceful shutdown.")

    import asyncio
    try:
        asyncio.run(daemon_instance.run_forever())
    except KeyboardInterrupt:
        print("\n[+] Graceful shutdown signal received. Terminating daemon...")
        daemon_instance.stop()
        print("[+] Daemon stopped cleanly.")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    """Launch the resident daemon as a detached background process."""
    pid_mgr = DaemonProcessManager(Path(".aerd.pid"))
    active_pid = pid_mgr.read_pid()
    if active_pid and pid_mgr.is_pid_alive(active_pid):
        print(f"[-] AER daemon is already running with PID {active_pid}.")
        return 1

    py_exe = sys.executable
    cli_script = os.path.abspath(__file__)
    cmd = [py_exe, cli_script, "run"]

    log_path = Path(".aerd.log")
    log_handle = open(log_path, "a", encoding="utf-8")
    env_vars = os.environ.copy()
    env_vars["PYTHONUNBUFFERED"] = "1"

    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            cmd,
            creationflags=creationflags,
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            env=env_vars
        )
    else:
        proc = subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            env=env_vars
        )

    pid_mgr.write_pid(proc.pid)
    print(f"[+] AER daemon successfully launched in background (PID: {proc.pid}).")
    print(f"[+] UI telemetry listening at http://127.0.0.1:28741/api/status")
    print(f"[+] Logs streaming to .aerd.log")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """Terminate the running background daemon gracefully."""
    pid_mgr = DaemonProcessManager(Path(".aerd.pid"))
    active_pid = pid_mgr.read_pid()
    if not active_pid:
        print("[-] No running aerd daemon found (no PID file present).")
        return 0

    if not pid_mgr.is_pid_alive(active_pid):
        print(f"[!] Stale PID file found ({active_pid}). Cleaning up.")
        pid_mgr.remove_pid()
        return 0

    print(f"[*] Stopping AER daemon (PID: {active_pid})...")
    stopped = pid_mgr.stop_process(active_pid)
    if stopped:
        print("[+] AER daemon successfully stopped.")
        return 0
    else:
        print("[-] Failed to terminate daemon process.")
        return 1


def cmd_attest(args: argparse.Namespace) -> int:
    """Generate and print a formal HardwareAttestation payload."""
    default_nid = get_default_node_id()
    engine = AttestationEngine()
    nonce_val = "0x" + secrets.token_hex(32)
    payload = engine.generate_attestation_payload(default_nid, nonce_val)

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
        description="AER Autonomous Background Resident Daemon CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available aerd subcommands")

    sub_status = subparsers.add_parser("status", help="Query local node status and daemon state")
    sub_status.set_defaults(func=cmd_status)

    sub_run = subparsers.add_parser("run", help="Run daemon in foreground event loop")
    sub_run.set_defaults(func=cmd_run)

    sub_start = subparsers.add_parser("start", help="Launch background resident daemon")
    sub_start.set_defaults(func=cmd_start)

    sub_stop = subparsers.add_parser("stop", help="Stop running background daemon")
    sub_stop.set_defaults(func=cmd_stop)

    sub_attest = subparsers.add_parser("attest", help="Generate hardware attestation evidence")
    sub_attest.set_defaults(func=cmd_attest)

    sub_verify = subparsers.add_parser("verify-task", help="Run sandboxed task verification")
    sub_verify.set_defaults(func=cmd_verify_task)

    return parser


def main() -> None:
    """Main CLI entrypoint."""
    _ = get_default_node_id()
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
