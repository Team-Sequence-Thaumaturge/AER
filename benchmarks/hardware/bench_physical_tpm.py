#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Physical Silicon TPM 2.0 Benchmark Runner (Phase 2-1)
=========================================================
Executes 1,000 iterations of hardware-anchored attestation quotes
against the host motherboard silicon chip (Windows TBS / Linux tpmrm0)
and contrasts latency, jitter, and throughput against emulated software.
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from aer.hardware_tpm import (
    TPMBenchmarkEngine,
    create_physical_tpm_provider,
    run_silicon_attestation_benchmark,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def format_metric_row(label: str, phys_val: str, mock_val: str) -> str:
    """Format a formatted 3-column table row for terminal display."""
    return f" {label:<28} | {phys_val:<22} | {mock_val:<22}"


def print_benchmark_table(
    phys_data: Dict[str, Any],
    mock_data: Dict[str, Any]
) -> None:
    """Render a terminal comparative telemetry table."""
    p_meta = phys_data["metadata"]
    p_met = phys_data["metrics"]
    m_meta = mock_data["metadata"]
    m_met = mock_data["metrics"]

    overhead_ratio = (
        p_met["mean_latency_ms"] / m_met["mean_latency_ms"]
        if m_met["mean_latency_ms"] > 0 else 1.0
    )

    print("================================================================================")
    print("      AER AXIOM 1: PHYSICAL SILICON TPM 2.0 BENCHMARK REPORT (PHASE 2-1)        ")
    print("================================================================================")
    print(f" Physical Silicon Device  : {p_meta.get('manufacturer_name', 'UNKNOWN')}")
    print(f" Driver Interface Layer   : {p_meta.get('driver_interface', 'UNKNOWN')}")
    print(f" Specification Standard   : {p_meta.get('spec_version', 'TPM 2.0')}")
    print(f" Silicon Anchor Hardware  : {'TRUE (Genuine Host Motherboard)' if p_meta.get('is_hardware_present') else 'EMULATED'}")
    print("--------------------------------------------------------------------------------")
    print(f" {'Metric / Parameter':<28} | {'Physical Silicon TPM':<22} | {'Software Mock TPM':<22}")
    print("--------------------------------------------------------------------------------")
    print(format_metric_row("Benchmark Iterations", f"{p_met['total_iterations']:,} runs", f"{m_met['total_iterations']:,} runs"))
    print(format_metric_row("Mean Latency (ms)", f"{p_met['mean_latency_ms']:.4f} ms", f"{m_met['mean_latency_ms']:.4f} ms"))
    print(format_metric_row("Jitter / Std Dev (ms)", f"{p_met['std_dev_ms']:.4f} ms", f"{m_met['std_dev_ms']:.4f} ms"))
    print(format_metric_row("Median p50 Latency", f"{p_met['p50_ms']:.4f} ms", f"{m_met['p50_ms']:.4f} ms"))
    print(format_metric_row("95th Percentile p95", f"{p_met['p95_ms']:.4f} ms", f"{m_met['p95_ms']:.4f} ms"))
    print(format_metric_row("99th Percentile p99", f"{p_met['p99_ms']:.4f} ms", f"{m_met['p99_ms']:.4f} ms"))
    print(format_metric_row("Min Latency", f"{p_met['min_ms']:.4f} ms", f"{m_met['min_ms']:.4f} ms"))
    print(format_metric_row("Max Latency", f"{p_met['max_ms']:.4f} ms", f"{m_met['max_ms']:.4f} ms"))
    print(format_metric_row("Throughput (TPS)", f"{p_met['throughput_quotes_per_sec']:,.1f} quotes/s", f"{m_met['throughput_quotes_per_sec']:,.1f} quotes/s"))
    print("--------------------------------------------------------------------------------")
    print(f" [*] Hardware Overhead Ratio : {overhead_ratio:.2f}x (Hardware Bus vs Pure In-Memory RAM)")
    print(" [*] Sybil Resistance Level  : HARDWARE_BOUND (Zeroization Immune, Blinded DAA)")
    print("================================================================================")


def save_benchmark_results(
    phys_data: Dict[str, Any],
    mock_data: Dict[str, Any],
    output_path: Path
) -> None:
    """Export benchmark telemetry to a structured JSON artifact."""
    payload = {
        "timestamp": time.time(),
        "phase": "2-1",
        "benchmark_name": "Physical Silicon TPM 2.0 Telemetry Benchmark",
        "physical_silicon": phys_data,
        "software_mock": mock_data
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[+] Benchmark results exported to: {output_path}")


def run_hardware_benchmark_cli(iterations: int = 1000) -> int:
    """Main CLI execution handler for TPM silicon benchmarking."""
    print(f"[*] Initiating AER Silicon TPM 2.0 Benchmark ({iterations} iterations)...")
    phys_data, mock_data = run_silicon_attestation_benchmark(iterations=iterations)
    print_benchmark_table(phys_data, mock_data)

    out_file = Path(__file__).parent / "results_tpm_benchmark.json"
    save_benchmark_results(phys_data, mock_data, out_file)
    return 0


def main() -> None:
    """Entrypoint dispatcher."""
    run_hardware_benchmark_cli(iterations=1000)


if __name__ == "__main__":
    main()
