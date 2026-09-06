#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Core Daemon Lifecycle Unit Tests (Phase 2-0)
================================================
Validates daemon orchestrator initialization, PID management,
tick state transitions, telemetry streaming, and graceful shutdown.
"""

import sys
import os
import time
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from aer.daemon import (
    DaemonConfig,
    DaemonProcessManager,
    DaemonTelemetryRecord,
    AERAutonomousDaemon,
    create_autonomous_daemon,
    get_daemon_telemetry,
)
from aer.cli import build_cli_parser


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_daemon_config_defaults() -> None:
    """Validate DaemonConfig default parameters and custom overrides."""
    default_config = DaemonConfig()
    assert default_config.host == "127.0.0.1"
    assert default_config.port == 28741
    assert default_config.tick_interval_seconds == 1.0

    custom_pid = ".test_custom.pid"
    custom_nid = "0xCustomNodeId"
    custom_config = DaemonConfig(
        node_id = custom_nid,
        host = "127.0.0.1",
        port = 28742,
        tick_interval_seconds = 0.5,
        pid_file_path = custom_pid
    )
    assert custom_config.port == 28742
    assert custom_config.node_id == "0xCustomNodeId"
    assert custom_config.pid_file == Path(custom_pid)
    print("  [PASS] test_daemon_config_defaults")


def test_daemon_process_manager() -> None:
    """Validate DaemonProcessManager PID file lifecycle and singleton check."""
    temp_pid_file = Path(".test_aerd.pid")
    mgr = DaemonProcessManager(temp_pid_file)

    mgr.remove_pid()
    assert mgr.read_pid() is None

    test_pid = os.getpid()
    mgr.write_pid(test_pid)
    assert mgr.read_pid() == test_pid
    assert mgr.is_pid_alive(test_pid) is True

    mgr.remove_pid()
    assert mgr.read_pid() is None
    print("  [PASS] test_daemon_process_manager")


def test_daemon_orchestrator_initialization() -> None:
    """Verify AERAutonomousDaemon constructs all underlying subsystem engines."""
    cfg = DaemonConfig(pid_file_path=".test_daemon_init.pid")
    daemon_obj = create_autonomous_daemon(cfg)

    assert daemon_obj.attestation is not None
    assert daemon_obj.verifier is not None
    assert daemon_obj.state_registry is not None
    assert daemon_obj.credit is not None
    assert daemon_obj.timelock is not None
    assert daemon_obj.netting is not None
    assert daemon_obj.mesh is not None
    assert daemon_obj.market is not None
    assert daemon_obj.ui_server is not None
    assert daemon_obj.is_active is False
    print("  [PASS] test_daemon_orchestrator_initialization")


def test_daemon_start_tick_stop() -> None:
    """Verify daemon start, tick cycle, telemetry payload, and graceful stop."""
    cfg = DaemonConfig(port=28749, pid_file_path=".test_tick.pid")
    daemon_obj = AERAutonomousDaemon(cfg)

    success = daemon_obj.start()
    assert success is True
    assert daemon_obj.is_active is True

    # Execute 3 manual tick cycles
    daemon_obj.tick()
    daemon_obj.tick()
    daemon_obj.tick()
    assert daemon_obj.total_ticks == 3

    telemetry = get_daemon_telemetry(daemon_obj)
    assert telemetry["status"] == "ONLINE"
    assert telemetry["processed_ticks"] == 3
    assert "uptime_seconds" in telemetry
    assert "reputation_mass_a" in telemetry

    daemon_obj.stop()
    assert daemon_obj.is_active is False
    print("  [PASS] test_daemon_start_tick_stop")


def test_daemon_async_lifecycle() -> None:
    """Verify async event loop execution and graceful cancellation."""
    cfg = DaemonConfig(port=28750, tick_interval_seconds=0.05, pid_file_path=".test_async.pid")
    daemon_obj = AERAutonomousDaemon(cfg)

    async def run_short_lived() -> None:
        task = asyncio.create_task(daemon_obj.run_forever())
        await asyncio.sleep(0.15)
        daemon_obj.stop()
        await task

    asyncio.run(run_short_lived())
    assert daemon_obj.total_ticks >= 1
    assert daemon_obj.is_active is False
    print("  [PASS] test_daemon_async_lifecycle")


def test_cli_parser_commands() -> None:
    """Verify that CLI subcommands are properly registered."""
    parser = build_cli_parser()
    subparsers_actions = [
        action for action in parser._actions if action.dest == "command"
    ]
    assert len(subparsers_actions) == 1
    choices = subparsers_actions[0].choices
    expected_cmds = ["status", "run", "start", "stop", "attest", "verify-task"]
    for cmd_name in expected_cmds:
        assert cmd_name in choices
    print("  [PASS] test_cli_parser_commands")


def run_all_daemon_lifecycle_tests() -> None:
    """Aggregate runner for all Phase 2-0 daemon lifecycle test fixtures."""
    print("==================================================================")
    print("AER Autonomous Daemon Lifecycle Test Suite (Phase 2-0)")
    print("==================================================================")
    test_daemon_config_defaults()
    test_daemon_process_manager()
    test_daemon_orchestrator_initialization()
    test_daemon_start_tick_stop()
    test_daemon_async_lifecycle()
    test_cli_parser_commands()
    print("==================================================================")
    print("ALL 6 DAEMON LIFECYCLE TESTS PASSED 100%")
    print("==================================================================")


if __name__ == "__main__":
    run_all_daemon_lifecycle_tests()
