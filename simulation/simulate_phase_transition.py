"""
AER Simulation 1: Trust Phase Transition vs Linear Slashing
Demonstrates:
  1. Traditional linear slashing as an absorbable cost of griefing for whales.
  2. AER non-linear phase transition avalanche (Omega_c = 0.05, bit-shift decay >> 1).
  3. Thermodynamic hysteresis: high work barrier to regain ground-state reputation.
"""

import sys
import math
from typing import Dict, List, Any, Tuple

sys.stdout.reconfigure(encoding="utf-8")


class TraditionalSlashingModel:
    """Simulates conventional linear penalties (-n flat fee or fixed slashing)."""

    def __init__ (self, initial_stake: float = 1000.0, penalty_per_defect: float = 10.0, exploit_gain: float = 25.0):
        self.stake = initial_stake
        self.penalty = penalty_per_defect
        self.gain = exploit_gain
        self.history: List[float] = [self.stake]

    def step_traditional(self, is_defect: bool) -> float:
        if is_defect:
            # Whale earns exploit reward and absorbs linear penalty
            self.stake += (self.gain - self.penalty)
        else:
            self.stake += 1.0
        self.history.append(self.stake)
        return self.stake


class AERPhaseTransitionModel:
    """
    Simulates statistical-mechanical phase transitions governed by Axiom 2 & Section 4.4.4.
    """

    def __init__(self, initial_mass: int = 1000, ground_state: int = 10, omega_critical: float = 0.05):
        self.mass = initial_mass
        self.ground_state = ground_state
        self.omega_critical = omega_critical
        self.total_completed = 0
        self.total_betrayals = 0
        self.is_boycotted = False
        self.history: List[int] = [self.mass]

    def get_betrayal_density(self) -> float:
        total = self.total_completed + self.total_betrayals
        if total == 0:
            return 0.0
        return self.total_betrayals / total

    def step_aer(self, is_defect: bool) -> int:
        if self.is_boycotted:
            # Trapped in insulating ground state A_0
            self.history.append(self.mass)
            return self.mass

        if is_defect:
            self.total_betrayals += 1
            omega = self.get_betrayal_density()
            if omega >= self.omega_critical:
                # Percolation threshold shattered: cascading bit-shift avalanche >> 1
                self.is_boycotted = True
                surplus = max(0, self.mass - self.ground_state)
                # Avalanche down to ground state
                self.mass = self.ground_state + (surplus >> 5)  # Drop >96% immediately
                if self.mass < self.ground_state:
                    self.mass = self.ground_state
            else:
                # Sub-critical minor friction
                self.mass = max(self.ground_state, self.mass - 5)
        else:
            self.total_completed += 1
            # Logarithmic bounded trust growth
            self.mass += int(max(1, 5 * math.log10(1 + self.total_completed)))

        self.history.append(self.mass)
        return self.mass


def render_ascii_comparison_chart(trad_hist: List[float], aer_hist: List[int], epochs: int = 25) -> str:
    """Renders a terminal ASCII comparison chart between the two trajectories."""
    lines = []
    lines.append("\n" + "=" * 72)
    lines.append("  REPUTATION / CAPITAL TRAJECTORY: TRADITIONAL SLASHING vs AER AVALANCHE")
    lines.append("=" * 72)
    lines.append(f" {'Epoch':<6} | {'Trad Stake (Linear Slashing)':<28} | {'AER Credit A (Phase Transition)':<30}")
    lines.append("-" * 72)

    step_interval = max(1, len(trad_hist) // epochs)
    indices = list(range(0, len(trad_hist), step_interval))
    if indices[-1] != len(trad_hist) - 1:
        indices.append(len(trad_hist) - 1)

    for idx in indices:
        t_val = trad_hist[idx]
        a_val = aer_hist[idx]
        t_bar = "#" * min(20, int(t_val / 60))
        a_bar = "*" * min(20, int(a_val / 50))
        lines.append(f" {idx:<6} | {t_val:>7.1f} {t_bar:<20} | {a_val:>7d} {a_bar:<20}")

    lines.append("=" * 72)
    lines.append(" Legend: [#] Traditional Whale Net Capital (Grows despite penalties)")
    lines.append("         [*] AER Credit A (Instantaneous Avalanche Collapse when Omega >= 0.05)")
    lines.append("=" * 72 + "\n")
    return "\n".join(lines)


def run_phase_transition_simulation(total_steps: int = 100, defect_ratio: float = 0.08) -> Dict[str, Any]:
    """Executes the comparative simulation run."""
    trad = TraditionalSlashingModel(initial_stake=1000.0, penalty_per_defect=10.0, exploit_gain=25.0)
    aer = AERPhaseTransitionModel(initial_mass=1000, ground_state=10, omega_critical=0.05)

    collapse_epoch = -1

    for step_idx in range(1, total_steps + 1):
        # Inject periodic malicious defection above Omega_c
        is_defect = (step_idx % int(1.0 / defect_ratio) == 0) if defect_ratio > 0 else False
        trad.step_traditional(is_defect)
        aer.step_aer(is_defect)

        if collapse_epoch == -1 and aer.is_boycotted:
            collapse_epoch = step_idx

    chart_str = render_ascii_comparison_chart(trad.history, aer.history, epochs=20)
    print(chart_str)

    results = {
        "total_steps": total_steps,
        "defect_ratio": defect_ratio,
        "trad_final_capital": trad.stake,
        "trad_capital_growth_percent": round(((trad.stake - 1000.0) / 1000.0) * 100.0, 2),
        "aer_final_credit_a": aer.mass,
        "aer_boycotted": aer.is_boycotted,
        "aer_collapse_epoch": collapse_epoch,
        "aer_loss_percent": round(((1000.0 - aer.mass) / 1000.0) * 100.0, 2),
        "hysteresis_recovery_work_required": 1000 - aer.mass
    }

    print(f"[*] Traditional Slashing Outcome: Whale capital increased from 1000.0 to {trad.stake:.1f} (+{results['trad_capital_growth_percent']}%)")
    print(f"[*] AER Phase Transition Outcome: Credit A collapsed from 1000 to {aer.mass} (-{results['aer_loss_percent']}%) at epoch {collapse_epoch}")
    print(f"[*] Thermodynamic Hysteresis: Offender requires {results['hysteresis_recovery_work_required']} uncompensated negentropy units to recover.\n")

    return results


if __name__ == "__main__":
    _sim_results = run_phase_transition_simulation(total_steps=100, defect_ratio=0.08)
