#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Mathematical Invariants Formal Verification Tests (Phase 2-4)
================================================================
Validates Z3 SMT Solver proofs for the 3 core invariants:
1. Asset Orthogonality (∂A_j / ∂Fiat ≡ 0)
2. Non-Inflationary Unbacked Supply Bound (Σ B_unbacked <= Σ C_i)
3. Deadlock-Free Priority Netting Convergence (Monotonic Cycle Elimination)
"""

import os
import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from proofs.formal_verification.verify_invariants import (
    AssetOrthogonalityProver,
    UnbackedSupplyBoundProver,
    DeadlockFreeNettingProver
)


def test_theorem_1_asset_orthogonality():
    """Verify Z3 proves fiat cannot purchase reputation without physical PoP."""
    prover = AssetOrthogonalityProver()
    _ = prover.__init__()
    res = prover.prove_orthogonality()
    assert res["is_proven"] is True
    assert "UNSAT" in res["smt_result"]
    assert res["solving_time_ms"] > 0


def test_theorem_2_unbacked_supply_bound():
    """Verify Z3 proves unbacked offline debt cannot exceed collective credit limits."""
    prover = UnbackedSupplyBoundProver()
    _ = prover.__init__()
    res = prover.prove_supply_bound()
    assert res["is_proven"] is True
    assert "UNSAT" in res["smt_result"]
    assert res["solving_time_ms"] > 0


def test_theorem_3_deadlock_free_priority_netting():
    """Verify Z3 proves cyclic debt reduction strictly eliminates edges and preserves balances."""
    prover = DeadlockFreeNettingProver()
    _ = prover.__init__()
    res = prover.prove_deadlock_freedom()
    assert res["is_proven"] is True
    assert "UNSAT" in res["smt_result"]
    assert res["solving_time_ms"] > 0


def test_formal_verification_results_json():
    """Verify exported formal verification JSON artifact exists and contains all 3 theorems."""
    out_json = Path(__file__).parent.parent.parent / "proofs" / "formal_verification" / "results_formal_verification.json"
    assert out_json.exists(), "results_formal_verification.json not found"

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["phase"] == "2-4"
    assert data["all_theorems_proven"] is True
    assert len(data["theorems"]) == 3
    for th in data["theorems"]:
        assert th["is_proven"] is True
