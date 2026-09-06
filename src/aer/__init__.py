"""
AER (Autonomous Existence & Recognition) Core Daemon Engine
==========================================================
Autonomous background daemon orchestrating hardware-anchored identity,
WASM fuel-metered execution sandboxes, non-linear trust phase transitions,
collateral-credit continuums, and peer-to-peer resource allocation.
"""

__version__ = "1.9.2"
__protocol_version__ = "v1"

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
]
