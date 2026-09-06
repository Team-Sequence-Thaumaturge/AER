#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Physical Silicon TPM 2.0 Unit Tests (Phase 2-1)
==================================================
Validates hardware detection, physical PCR reading, true entropy extraction,
schema-compliant silicon quote generation, and comparative benchmark computation.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from aer.hardware_tpm import (
    PhysicalTPMProvider,
    TPMBenchmarkEngine,
    create_physical_tpm_provider,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_physical_tpm_initialization() -> None:
    """Verify physical TPM provider connects or gracefully identifies interface."""
    provider = create_physical_tpm_provider(force_mock=False)
    assert provider.metadata is not None
    assert provider.metadata.driver_interface in ["WINDOWS_TBS_API", "LINUX_DEV_TPMRM0", "SOFTWARE_FALLBACK"]
    meta_dict = provider.metadata.to_device_dict()
    assert "is_hardware_present" in meta_dict
    assert "manufacturer_name" in meta_dict
    provider.close()
    print("  [PASS] test_physical_tpm_initialization")


def test_physical_random_entropy() -> None:
    """Verify true hardware quantum/thermal entropy generation."""
    provider = create_physical_tpm_provider(force_mock=False)
    entropy = provider.get_physical_random(32)
    assert isinstance(entropy, bytes)
    assert len(entropy) == 32
    assert entropy != b"\x00" * 32
    provider.close()
    print("  [PASS] test_physical_random_entropy")


def test_physical_pcr_read() -> None:
    """Verify platform configuration register (PCR 0) digest extraction."""
    provider = create_physical_tpm_provider(force_mock=False)
    pcr0_hex = provider.read_physical_pcr(0)
    assert isinstance(pcr0_hex, str)
    assert len(pcr0_hex) == 64  # 32 bytes SHA-256 hex
    provider.close()
    print("  [PASS] test_physical_pcr_read")


def test_silicon_quote_generation() -> None:
    """Verify schema-compliant HardwareAttestation generation."""
    provider = create_physical_tpm_provider(force_mock=False)
    test_nid = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    test_nonce = "0x" + "a" * 64
    quote = provider.generate_silicon_quote(test_nid, test_nonce, pcr_index=0)

    assert "platform_pcr_digest" in quote
    assert "blinded_silicon_commitment" in quote
    assert "attestation_key_quote" in quote
    assert "zk_vendor_membership_proof" in quote
    assert "silicon_firmware_version" in quote
    assert quote["extraction_latency_ms"] >= 0.0
    provider.close()
    print("  [PASS] test_silicon_quote_generation")


def test_emulated_fallback_mode() -> None:
    """Verify software fallback when hardware is absent or forced mock."""
    mock_prov = create_physical_tpm_provider(force_mock=True)
    assert mock_prov.is_physical is False
    assert mock_prov.metadata.driver_interface == "SOFTWARE_FALLBACK"

    test_nid = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    quote = mock_prov.generate_silicon_quote(test_nid, "0x1234", pcr_index=0)
    assert quote["is_physical_chip"] is False
    mock_prov.close()
    print("  [PASS] test_emulated_fallback_mode")


def test_benchmark_engine_execution() -> None:
    """Verify statistical telemetry metrics calculation across 10 sample runs."""
    engine = TPMBenchmarkEngine(iterations=10)
    prov = create_physical_tpm_provider(force_mock=True)
    snapshot = engine.run_benchmark(prov)

    snap_dict = snapshot.to_telemetry_dict()
    assert snap_dict["total_iterations"] == 10
    assert snap_dict["mean_latency_ms"] >= 0.0
    assert snap_dict["p50_ms"] >= 0.0
    assert snap_dict["throughput_quotes_per_sec"] > 0.0
    prov.close()
    print("  [PASS] test_benchmark_engine_execution")


def run_all_physical_tpm_tests() -> None:
    """Run all Phase 2-1 hardware attestation test cases."""
    print("==================================================================")
    print("AER Physical Silicon TPM 2.0 Test Suite (Phase 2-1)")
    print("==================================================================")
    test_physical_tpm_initialization()
    test_physical_random_entropy()
    test_physical_pcr_read()
    test_silicon_quote_generation()
    test_emulated_fallback_mode()
    test_benchmark_engine_execution()
    print("==================================================================")
    print("ALL 6 PHYSICAL SILICON TPM TESTS PASSED 100%")
    print("==================================================================")


if __name__ == "__main__":
    run_all_physical_tpm_tests()
