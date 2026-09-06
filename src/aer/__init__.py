"""
AER (Autonomous Existence & Recognition) Core Daemon Engine
==========================================================
Autonomous background daemon orchestrating hardware-anchored identity,
WASM fuel-metered execution sandboxes, non-linear trust phase transitions,
collateral-credit continuums, and peer-to-peer resource allocation.
"""

__version__ = "2.0.1"
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
from .hardware_tpm import (
    TPMDeviceMetadata,
    PhysicalTPMProvider,
    TPMTelemetrySnapshot,
    TPMBenchmarkEngine,
    create_physical_tpm_provider,
    run_silicon_attestation_benchmark,
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
    "TPMDeviceMetadata",
    "PhysicalTPMProvider",
    "TPMTelemetrySnapshot",
    "TPMBenchmarkEngine",
    "create_physical_tpm_provider",
    "run_silicon_attestation_benchmark",
]
