"""
AER (Autonomous Existence & Recognition) Core Daemon Engine
==========================================================
Autonomous background daemon orchestrating hardware-anchored identity,
WASM fuel-metered execution sandboxes, non-linear trust phase transitions,
collateral-credit continuums, and peer-to-peer resource allocation.
"""

__version__ = "2.0.0"
__protocol_version__ = "v2"

from .attestation import AttestationEngine, SoftwareMockTPMProvider
from .verifier import ExecutionSandboxVerifier
from .state import StateMachineRegistry, TrustPhaseManager
from .credit import CollateralCreditContinuum
from .guild import GuildChannelManager
from .timelock import OptimisticTimelockManager
from .netting import PriorityNettingEngine
from .p2p_mesh import P2PMeshRouter
from .market import P2PResourceMarket
from .ui_server import AERLocalUIServer
from .daemon import (
    DaemonConfig,
    DaemonTelemetryRecord,
    DaemonProcessManager,
    AERAutonomousDaemon,
    create_autonomous_daemon,
    get_daemon_telemetry,
)

__all__ = [
    "AttestationEngine",
    "SoftwareMockTPMProvider",
    "ExecutionSandboxVerifier",
    "StateMachineRegistry",
    "TrustPhaseManager",
    "CollateralCreditContinuum",
    "GuildChannelManager",
    "OptimisticTimelockManager",
    "PriorityNettingEngine",
    "P2PMeshRouter",
    "P2PResourceMarket",
    "AERLocalUIServer",
    "DaemonConfig",
    "DaemonTelemetryRecord",
    "DaemonProcessManager",
    "AERAutonomousDaemon",
    "create_autonomous_daemon",
    "get_daemon_telemetry",
]
