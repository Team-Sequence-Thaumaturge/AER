#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Collateral-Credit Continuum Engine
======================================
Calculates dynamic collateral requirements and uncollateralized mutual credit limits
as a function of reputation mass A_j (AER Section 4.3).

Features:
- Mandatory 100% upfront escrow for ground-state nodes (A_0 -> C_req = 1.0)
- Logarithmic collateral relaxation curve unlocking mutual credit for high-reputation nodes
- Credit line ceiling computation preventing systemic liquidity over-extension
"""

import math
from typing import Dict, Any, Tuple


class CollateralCreditContinuum:
    """
    Computes required collateral ratios and allowable uncollateralized debt limits.
    """

    def __init__(self, ground_state_mass: int = 10, alpha: float = 0.35):
        self.a_0 = ground_state_mass
        self.alpha = alpha  # Credit slope parameter

    def calculate_required_collateral_ratio(self, reputation_mass: int) -> float:
        """
        Calculate required collateral ratio C_req in range [0.0, 1.0].
        Formula: C_req = max(0.0, min(1.0, 1.0 - alpha * ln(A_j / A_0)))
        """
        if reputation_mass <= self.a_0:
            return 1.0  # 100% upfront escrow strictly required for base/new nodes

        ratio = reputation_mass / self.a_0
        relaxation = self.alpha * math.log(ratio)
        required = 1.0 - relaxation
        return max(0.0, min(1.0, required))

    def calculate_mutual_credit_limit(self, reputation_mass: int, base_unit: int = 1000) -> int:
        """
        Calculate allowable unsecured credit limit in atomic Credit B (AER-B) units.
        Nodes at A_0 receive 0 unsecured credit.
        Baseline node at A_j = 100 receives 1,000 AER-B credit line, scaling linearly.
        """
        if reputation_mass <= self.a_0:
            return 0

        excess_mass = reputation_mass - self.a_0
        # Baseline: at excess_mass = 90 (A_j = 100), limit is exactly 1,000 AER-B
        return max(0, int((excess_mass / 90.0) * base_unit))

    def evaluate_task_collateral(
        self,
        reputation_mass: int,
        task_bounty: int
    ) -> Dict[str, Any]:
        """
        Evaluate full collateral requirements for a proposed task escrow.
        """
        c_req = self.calculate_required_collateral_ratio(reputation_mass)
        mandatory_escrow = int(task_bounty * c_req)
        credit_covered = task_bounty - mandatory_escrow
        credit_limit = self.calculate_mutual_credit_limit(reputation_mass)

        is_admissible = (credit_covered <= credit_limit)

        return {
            "reputation_mass": reputation_mass,
            "collateral_ratio": round(c_req, 4),
            "mandatory_upfront_escrow": mandatory_escrow,
            "credit_unsecured_amount": credit_covered,
            "max_credit_limit": credit_limit,
            "is_admissible": is_admissible
        }


if __name__ == "__main__":
    _default_engine = CollateralCreditContinuum()

