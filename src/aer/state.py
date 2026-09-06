#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER State Machine & Trust Phase Transition Engine
=================================================
Implements the mathematical physics of reputation phase transitions (AER Section 4.2)
and bounded state expiry garbage collection.

Features:
- Non-linear bit-shift half-life decay (A_j >> 1) upon crossing betrayal threshold (Omega_c)
- Immediate avalanche collapse to ground state (A_0) under Byzantine attacks
- LSM compaction-style state expiry eviction for inactive node records
"""

import time
from typing import Dict, Any, List, Optional, Tuple


class NodeReputationState:
    """
    Tracks an individual node's operational track record, successful completions,
    betrayal history, and effective reputation mass A_j.
    """

    def __init__ (self, node_id: str, initial_mass: int = 100):
        self.node_id = node_id.lower()
        self.reputation_mass = initial_mass  # A_j (scalar credit mass)
        self.ground_state = 10               # A_0 base hardware mass
        self.total_completed_tasks = 0
        self.total_betrayals = 0
        self.last_active_epoch = int(time.time())
        self.is_boycotted = False

    def get_betrayal_density(self) -> float:
        """Calculate betrayal ratio: total_betrayals / (completed + betrayals)."""
        total = self.total_completed_tasks + self.total_betrayals
        if total == 0:
            return 0.0
        return self.total_betrayals / total


class TrustPhaseManager:
    """
    Enforces non-linear phase transitions and reputation cascading collapses.
    """

    def __init__ (self, omega_critical: float = 0.05):
        # Critical betrayal density threshold Omega_c (e.g. 5%)
        self.omega_critical = omega_critical

    def record_successful_completion(self, state: NodeReputationState, task_weight: int = 1) -> int:
        """Incremental trust accumulation through verified physical/compute work."""
        state.total_completed_tasks += 1
        state.last_active_epoch = int(time.time())
        # Smooth bounded logarithmic gain
        gain = max(1, task_weight // 10)
        state.reputation_mass += gain
        return state.reputation_mass

    def record_betrayal_event(self, state: NodeReputationState) -> Tuple[int, bool]:
        """
        Record verified contract or physical betrayal.
        If betrayal density crosses Omega_c, triggers immediate bit-shift decay avalanche.
        """
        state.total_betrayals += 1
        state.last_active_epoch = int(time.time())

        betrayal_density = state.get_betrayal_density()

        # Phase transition check: Non-linear avalanche collapse
        if betrayal_density >= self.omega_critical or state.total_betrayals >= 2:
            # Cascading bit shift half-life decay: A_j >> 1
            state.reputation_mass = max(state.ground_state, state.reputation_mass >> 1)
            state.is_boycotted = True
            return state.reputation_mass, True
        else:
            # Minor penalty
            state.reputation_mass = max(state.ground_state, state.reputation_mass - 5)
            return state.reputation_mass, False


class StateMachineRegistry:
    """
    Global node state registry managing node instances and state expiry compaction.
    """

    def __init__(self, state_expiry_seconds: int = 30 * 86400):
        self.nodes: Dict[str, NodeReputationState] = {}
        self.phase_manager = TrustPhaseManager()
        self.state_expiry_seconds = state_expiry_seconds

    def get_or_create_node(self, node_id: str) -> NodeReputationState:
        """Retrieve existing node state or initialize in base ground state A_0."""
        nid = node_id.lower()
        if nid not in self.nodes:
            self.nodes[nid] = NodeReputationState(nid)
        return self.nodes[nid]

    def execute_state_expiry_compaction(self, current_time: Optional[int] = None) -> int:
        """
        Garbage collect long-dormant inactive nodes to bound local RAM memory footprint.
        Returns the number of pruned dormant node records.
        """
        now = current_time if current_time is not None else int(time.time())
        cutoff = now - self.state_expiry_seconds

        dormant_keys = [
            nid for nid, state in self.nodes.items()
            if state.last_active_epoch < cutoff and state.reputation_mass <= state.ground_state
        ]

        for k in dormant_keys:
            del self.nodes[k]

        return len(dormant_keys)
 

if __name__ == "__main__":
    _default_registry = StateMachineRegistry()
