"""
AER Master Simulation Runner (Phase 4 CLI Harness)
Executes and benchmarks all 6 economic and distributed system simulations in sequence.
"""

import os
import sys
import time
from typing import Dict, Any, List, Tuple

# Ensure project root and src are in sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src"))
sys.path.insert(0, _PROJECT_ROOT)

sys.stdout.reconfigure(encoding="utf-8")

from simulation.simulate_phase_transition import run_phase_transition_simulation
from simulation.simulate_offline_netting import run_offline_netting_simulation
from simulation.simulate_supernova import run_supernova_simulation
from simulation.simulate_macro_arbitrage import run_macro_arbitrage_simulation
from simulation.simulate_black_market import run_black_market_simulation
from simulation.simulate_hardware_handover import run_hardware_handover_simulation


def execute_single_simulation(sim_name: str, sim_callable) -> Tuple[bool, float, Dict[str, Any]]:
    """Runs a single simulation while recording elapsed wall-clock execution time."""
    start_time = time.perf_counter()
    try:
        results = sim_callable()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return True, elapsed_ms, results
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        print(f"[-] Execution failure in {sim_name}: {exc}")
        return False, elapsed_ms, {}


def format_benchmark_report_table(records: List[Tuple[str, bool, float]]) -> str:
    """Formats an ASCII benchmark latency table across all simulation targets."""
    lines = []
    lines.append("\n" + "=" * 74)
    lines.append("     AER PHASE 4: MASTER SIMULATION SUITE BENCHMARK REPORT")
    lines.append("=" * 74)
    lines.append(f" {'ID':<3} | {'Simulation Engine Target':<42} | {'Latency':<12} | {'Status':<8}")
    lines.append("-" * 74)

    total_time_ms = 0.0
    for idx, (name, success, latency) in enumerate(records, 1):
        status_str = "PASS" if success else "FAIL"
        lines.append(f" {idx:<3} | {name:<42} | {latency:>8.2f} ms | {status_str:<8}")
        total_time_ms += latency

    lines.append("=" * 74)
    lines.append(f" Cumulative Execution Time: {total_time_ms:.2f} ms")
    lines.append(" Status: ALL 6 ECONOMIC & DISTRIBUTED SIMULATIONS EXECUTED (100%)")
    lines.append("=" * 74 + "\n")
    return "\n".join(lines)


def run_all_simulations_cli() -> bool:
    """Entrypoint executing all 6 simulations in benchmark mode."""
    print("=" * 74)
    print("Starting AER Phase 4 Master Simulation Suite Execution...")
    print("=" * 74)

    simulation_targets = [
        ("Trust Phase Transition & Avalanche", lambda: run_phase_transition_simulation(100, 0.08)),
        ("Offline Multi-Charging & Priority Netting", run_offline_netting_simulation),
        ("Guild Supernova & Bulkhead Containment", lambda: run_supernova_simulation(20, 10)),
        ("Macro Arbitrage, Cartel & Energy Peg", run_macro_arbitrage_simulation),
        ("Serverless P2P Swarm & Digital Loot", lambda: run_black_market_simulation(1000)),
        ("Hardware Handover & Disaster Recovery", run_hardware_handover_simulation)
    ]

    records = []
    all_success = True

    for name, callable_fn in simulation_targets:
        success, latency, _ = execute_single_simulation(name, callable_fn)
        records.append((name, success, latency))
        if not success:
            all_success = False

    report = format_benchmark_report_table(records)
    print(report)
    return all_success


if __name__ == "__main__":
    _cli_success = run_all_simulations_cli()
    if not _cli_success:
        sys.exit(1)
    sys.exit(0)
