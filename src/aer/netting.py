#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Bounty-Futures Priority Netting Engine
==========================================
Coordinates asynchronous mutual credit clearing and priority liability netting
(AER Section 6.3).

Features:
- Offline IOU ledger ingestion and verification
- Delay risk factor (gamma_offline) compounding
- Automatic revenue interception and creditor priority waterfall execution
"""

import time
from typing import Dict, Any, List, Optional, Tuple


class PromissoryNote:
    """Represents an ingested offline IOU credit claim."""

    def __init__ (
        self,
        iou_id: str,
        debtor_id: str,
        creditor_id: str,
        principal_credit_b: int,
        offline_risk_factor: float = 1.0,
        nonce: int = 0
    ):
        self.iou_id = iou_id
        self.debtor_id = debtor_id.lower()
        self.creditor_id = creditor_id.lower()
        self.principal_credit_b = principal_credit_b
        self.risk_factor = max(1.0, offline_risk_factor)
        self.effective_liability = int(principal_credit_b * self.risk_factor)
        self.remaining_liability = self.effective_liability
        self.nonce = nonce
        self.created_at = int(time.time())
        self.is_fully_netted = False


class PriorityNettingEngine:
    """
    Manages outstanding mutual credit debt and executes priority settlement waterfalls.
    """

    def __init__(self):
        # Debtor ID -> List of PromissoryNote
        self.debt_ledger: Dict[str, List[PromissoryNote]] = {}

    def register_offline_iou(
        self,
        iou_id: str,
        debtor_id: str,
        creditor_id: str,
        principal_credit_b: int,
        risk_factor: float = 1.0,
        nonce: int = 0
    ) -> PromissoryNote:
        """Record a validated offline promissory note onto the local netting ledger."""
        note = PromissoryNote(iou_id, debtor_id, creditor_id, principal_credit_b, risk_factor, nonce)
        did = debtor_id.lower()
        if did not in self.debt_ledger:
            self.debt_ledger[did] = []
        self.debt_ledger[did].append(note)
        return note

    def get_total_outstanding_debt(self, debtor_id: str) -> int:
        """Calculate total unnetted liability for a node."""
        did = debtor_id.lower()
        notes = self.debt_ledger.get(did, [])
        return sum(n.remaining_liability for n in notes if not n.is_fully_netted)

    def execute_priority_waterfall(
        self,
        debtor_id: str,
        inflow_revenue: int
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Intercept newly arrived task bounty and automatically clear pending claims.
        Returns: (total_deducted, net_worker_payout, settlement_records)
        """
        did = debtor_id.lower()
        notes = self.debt_ledger.get(did, [])
        remaining_revenue = inflow_revenue
        total_deducted = 0
        settlements = []

        for note in notes:
            if note.is_fully_netted or remaining_revenue <= 0:
                continue

            payment = min(note.remaining_liability, remaining_revenue)
            note.remaining_liability -= payment
            remaining_revenue -= payment
            total_deducted += payment

            if note.remaining_liability == 0:
                note.is_fully_netted = True

            settlements.append({
                "iou_id": note.iou_id,
                "creditor_id": note.creditor_id,
                "paid_amount": payment,
                "remaining_on_note": note.remaining_liability,
                "note_cleared": note.is_fully_netted
            })

        net_worker_payout = remaining_revenue
        return total_deducted, net_worker_payout, settlements


if __name__ == "__main__":
    _default_netting_engine = PriorityNettingEngine()

