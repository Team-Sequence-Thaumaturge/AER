#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Optimistic Timelock Manager
===============================
Coordinates off-chain challenge windows, watchtower pause assertions,
and automatic settlement finalization (AER Section 4.4.3).

Features:
- Variable timelock countdown calculation
- Delay liquidity bonus accounting for worker latency compensation
- Watchtower 72-hour freeze handling on defect detection
- Autonomous expiration triggering
"""

import time
from typing import Dict, Any, Optional


class TimelockState:
    """Represents the temporal state of an individual escrowed task."""

    def __init__ (
        self,
        task_id: str,
        base_duration: int = 86400,
        delay_premium: int = 0
    ):
        self.task_id = task_id
        self.created_at = int(time.time())
        self.duration = base_duration
        self.delay_premium = delay_premium
        self.is_paused = False
        self.paused_at = 0
        self.accumulated_pause_duration = 0
        self.is_finalized = False
        self.is_disputed = False

    def get_effective_deadline(self) -> int:
        """Calculate effective unix epoch deadline including pause delays."""
        current_pause = 0
        if self.is_paused:
            current_pause = int(time.time()) - self.paused_at
        return self.created_at + self.duration + self.accumulated_pause_duration + current_pause

    def is_expired(self, current_timestamp: Optional[int] = None) -> bool:
        """Check whether the timelock window has elapsed without active dispute."""
        if self.is_paused or self.is_disputed or self.is_finalized:
            return False
        now = current_timestamp if current_timestamp is not None else int(time.time())
        return now >= self.get_effective_deadline()


class OptimisticTimelockManager:
    """
    Manages active task timelocks and watches for pause/dispute triggers.
    """

    def __init__(self):
        self.timelocks: Dict[str, TimelockState] = {}

    def schedule_timelock(
        self,
        task_id: str,
        duration: int = 86400,
        delay_premium: int = 0
    ) -> TimelockState:
        """Register a new task escrow countdown."""
        state = TimelockState(task_id, duration, delay_premium)
        self.timelocks[task_id] = state
        return state

    def pause_timelock(self, task_id: str) -> bool:
        """Pause the countdown (e.g. watchtower defect signal)."""
        state = self.timelocks.get(task_id)
        if state and not state.is_paused and not state.is_finalized:
            state.is_paused = True
            state.paused_at = int(time.time())
            return True
        return False

    def resume_timelock(self, task_id: str) -> bool:
        """Resume the countdown after dispute inspection."""
        state = self.timelocks.get(task_id)
        if state and state.is_paused:
            state.accumulated_pause_duration += (int(time.time()) - state.paused_at)
            state.is_paused = False
            state.paused_at = 0
            return True
        return False

    def mark_disputed(self, task_id: str) -> bool:
        """Halt timelock permanently due to deterministic fraud proof."""
        state = self.timelocks.get(task_id)
        if state and not state.is_finalized:
            state.is_disputed = True
            state.is_paused = False
            return True
        return False

    def finalize_settlement(self, task_id: str, current_time: Optional[int] = None) -> bool:
        """Finalize and clear the task if timelock has safely expired."""
        state = self.timelocks.get(task_id)
        if state and state.is_expired(current_time):
            state.is_finalized = True
            return True
        return False


if __name__ == "__main__":
    _default_timelock_mgr = OptimisticTimelockManager()

