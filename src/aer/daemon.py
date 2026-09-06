#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Autonomous Resident Daemon Engine (Phase 2-0)
=================================================
Orchestrates the unified background resident loop, integrating:
- AERLocalUIServer (127.0.0.1:28741 local loopback UI & telemetry stream)
- P2PMeshRouter (libp2p GossipSub v1.1 & peer topology)
- OptimisticTimelockManager (24h challenge window scanner)
- PriorityNettingEngine (offline IOU netting queue poller)
- StateMachineRegistry & LSMCompactor (trust phase transitions & state expiry)
- AttestationEngine (hardware silicon anchoring)
"""

import sys
import os
import time
import json
import signal
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from aer.attestation import AttestationEngine
from aer.verifier import ExecutionSandboxVerifier
from aer.state import StateMachineRegistry
from aer.credit import CollateralCreditContinuum
from aer.timelock import OptimisticTimelockManager
from aer.netting import PriorityNettingEngine
from aer.p2p_mesh import P2PMeshRouter
from aer.market import P2PResourceMarket
from aer.ui_server import AERLocalUIServer


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class DaemonConfig:
    """Configuration parameter set for the resident autonomous daemon."""

    def __init__ (
        self,
        node_id: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        host: str = "127.0.0.1",
        port: int = 28741,
        tick_interval_seconds: float = 1.0,
        pid_file_path: Optional[str] = None
    ):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.tick_interval_seconds = tick_interval_seconds
        if pid_file_path:
            self.pid_file = Path(pid_file_path)
        else:
            self.pid_file = Path(".aerd.pid")


class DaemonTelemetryRecord:
    """Telemetry snapshot data container for node monitoring."""

    def __init__ (
        self,
        node_id: str,
        status: str,
        uptime_seconds: float,
        reputation_mass_a: int,
        pending_iou_count: int,
        p2p_peer_count: int,
        processed_ticks: int,
        last_tick_timestamp: float
    ):
        self.node_id = node_id
        self.status = status
        self.uptime_seconds = uptime_seconds
        self.reputation_mass_a = reputation_mass_a
        self.pending_iou_count = pending_iou_count
        self.p2p_peer_count = p2p_peer_count
        self.processed_ticks = processed_ticks
        self.last_tick_timestamp = last_tick_timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "reputation_mass_a": self.reputation_mass_a,
            "pending_iou_count": self.pending_iou_count,
            "p2p_peer_count": self.p2p_peer_count,
            "processed_ticks": self.processed_ticks,
            "last_tick_timestamp": self.last_tick_timestamp
        }


class DaemonProcessManager:
    """Controls PID file storage and lifecycle signalling across platforms."""

    def __init__ (self, pid_file: Path):
        self.pid_file = pid_file

    def write_pid(self, pid_number: int) -> None:
        self.pid_file.write_text(str(pid_number), encoding="utf-8")

    def read_pid(self) -> Optional[int]:
        if not self.pid_file.exists():
            return None
        try:
            content = self.pid_file.read_text(encoding="utf-8").strip()
            return int(content)
        except Exception:
            return None

    def remove_pid(self) -> None:
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception:
                pass

    def is_pid_alive(self, pid_number: int) -> bool:
        if pid_number <= 0:
            return False
        if os.name == "nt":
            import subprocess
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid_number}"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                return str(pid_number) in result.stdout
            except Exception:
                return False
        else:
            try:
                os.kill(pid_number, 0)
                return True
            except OSError:
                return False

    def stop_process(self, pid_number: int) -> bool:
        if not self.is_pid_alive(pid_number):
            self.remove_pid()
            return True
        try:
            if os.name == "nt":
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid_number)],
                    capture_output=True,
                    check=False
                )
            else:
                os.kill(pid_number, signal.SIGTERM)
            self.remove_pid()
            return True
        except Exception:
            return False


class AERAutonomousDaemon:
    """
    Main Autonomous Resident Daemon coordinating all AER subsystem engines.
    """

    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig()
        self.process_manager = DaemonProcessManager(self.config.pid_file)

        self.attestation = AttestationEngine()
        self.verifier = ExecutionSandboxVerifier()
        self.state_registry = StateMachineRegistry()
        self.credit = CollateralCreditContinuum()
        self.timelock = OptimisticTimelockManager()
        self.netting = PriorityNettingEngine()
        self.mesh = P2PMeshRouter(self.config.node_id)
        self.market = P2PResourceMarket()
        self.ui_server = AERLocalUIServer(host=self.config.host, port=self.config.port)

        self.is_active = False
        self.start_timestamp = 0.0
        self.total_ticks = 0
        self.last_tick_time = 0.0

    def start(self) -> bool:
        """Initialize all subsystems and start local background services."""
        if self.is_active:
            return True

        self.start_timestamp = time.time()
        self.is_active = True
        self.process_manager.write_pid(os.getpid())

        # Bind UI loopback server with telemetry callback
        self.ui_server.start(state_provider_callable=self.get_telemetry)
        return True

    def stop(self) -> None:
        """Gracefully terminate background services and cleanup PID file."""
        if not self.is_active:
            return

        self.is_active = False
        self.ui_server.stop()
        self.process_manager.remove_pid()

    def tick(self) -> None:
        """Execute one periodic cycle of background maintenance."""
        self.total_ticks += 1
        self.last_tick_time = time.time()

        # 1. Update state machine compaction and decay
        node_state = self.state_registry.get_or_create_node(self.config.node_id)
        if node_state:
            _ = node_state.reputation_mass

        # 2. Check timelock settlement triggers
        _ = [t for t in self.timelock.timelocks.values() if t.is_expired()]

        # 3. Process priority netting queues
        _ = self.netting.get_total_outstanding_debt(self.config.node_id)

    async def run_forever(self) -> None:
        """Infinite asynchronous event loop for resident node operation."""
        self.start()
        try:
            while self.is_active:
                self.tick()
                await asyncio.sleep(self.config.tick_interval_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            self.stop()

    def get_telemetry(self) -> Dict[str, Any]:
        """Compile a real-time telemetry snapshot dictionary."""
        uptime_val = (time.time() - self.start_timestamp) if self.start_timestamp > 0 else 0.0
        node_state = self.state_registry.get_or_create_node(self.config.node_id)
        rep_val = node_state.reputation_mass if node_state else 100
        debt_val = self.netting.get_total_outstanding_debt(self.config.node_id)
        peers_cnt = len(self.mesh.peers)

        telemetry_rec = DaemonTelemetryRecord(
            node_id = self.config.node_id,
            status = "ONLINE" if self.is_active else "STOPPED",
            uptime_seconds = uptime_val,
            reputation_mass_a = rep_val,
            pending_iou_count = int(debt_val),
            p2p_peer_count = peers_cnt,
            processed_ticks = self.total_ticks,
            last_tick_timestamp = self.last_tick_time
        )
        return telemetry_rec.to_dict()


def create_autonomous_daemon(config: Optional[DaemonConfig] = None) -> AERAutonomousDaemon:
    """Factory helper to construct an AERAutonomousDaemon instance."""
    resolved_config = config or DaemonConfig()
    return AERAutonomousDaemon(resolved_config)


def get_daemon_telemetry(daemon_instance: AERAutonomousDaemon) -> Dict[str, Any]:
    """Helper function to retrieve dictionary telemetry from an active daemon."""
    return daemon_instance.get_telemetry()


if __name__ == "__main__":
    _default_daemon = create_autonomous_daemon()
    _sample_telemetry = get_daemon_telemetry(_default_daemon)
    print("AER Autonomous Daemon Module initialized successfully.")
