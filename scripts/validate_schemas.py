#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Protocol Schema Validation Harness
======================================
Automated verification suite validating all 7 core machine-to-machine JSON schemas
and corresponding valid/invalid test payloads against JSON Schema Draft-07 specifications.

Compliance:
- Draft-07 Meta-Schema Validation
- Positive & Negative Boundary Tests
- SAPQ 4-Phase Cross-Parsing Conformance
"""

import os
import sys
import json
from pathlib import Path
import jsonschema
from jsonschema import Draft7Validator, ValidationError


def get_project_root() -> Path:
    """Return the absolute path to the AER project root directory."""
    return Path(__file__).resolve().parent.parent


def load_json_file(file_path: Path) -> dict:
    """Load and parse a JSON file from disk."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema_structure(schema_path: Path) -> dict:
    """Validate that the schema itself conforms to Draft-07 meta-schema."""
    schema_data = load_json_file(schema_path)
    Draft7Validator.check_schema(schema_data)
    return schema_data


def run_schema_verification() -> bool:
    """
    Execute full validation matrix across all 7 schemas and 14 test fixtures.
    Returns True if all tests pass, False otherwise.
    """
    root_dir = get_project_root()
    schemas_dir = root_dir / "schemas"
    examples_dir = schemas_dir / "examples"

    schema_test_matrix = [
        {
            "name": "HardwareAttestation",
            "schema_file": "HardwareAttestation.schema.json",
            "valid_example": "valid_hardware_attestation.json",
            "invalid_example": "invalid_hardware_attestation.json"
        },
        {
            "name": "ExecutionReceipt",
            "schema_file": "ExecutionReceipt.schema.json",
            "valid_example": "valid_execution_receipt.json",
            "invalid_example": "invalid_execution_receipt.json"
        },
        {
            "name": "OfflineIOU",
            "schema_file": "OfflineIOU.schema.json",
            "valid_example": "valid_offline_iou.json",
            "invalid_example": "invalid_offline_iou.json"
        },
        {
            "name": "DeterministicFraudProof",
            "schema_file": "DeterministicFraudProof.schema.json",
            "valid_example": "valid_deterministic_fraud_proof.json",
            "invalid_example": "invalid_deterministic_fraud_proof.json"
        },
        {
            "name": "MarketOrder",
            "schema_file": "MarketOrder.schema.json",
            "valid_example": "valid_market_order.json",
            "invalid_example": "invalid_market_order.json"
        },
        {
            "name": "HardwareMigration",
            "schema_file": "HardwareMigration.schema.json",
            "valid_example": "valid_hardware_migration.json",
            "invalid_example": "invalid_hardware_migration.json"
        },
        {
            "name": "PhysicalDispute",
            "schema_file": "PhysicalDispute.schema.json",
            "valid_example": "valid_physical_dispute.json",
            "invalid_example": "invalid_physical_dispute.json"
        }
    ]

    print("==================================================================")
    print("AER Core Protocol: Automated JSON Schema Validation Harness")
    print("==================================================================")

    all_passed = True
    passed_schemas_count = 0

    for test_case in schema_test_matrix:
        schema_name = test_case["name"]
        schema_file = schemas_dir / test_case["schema_file"]
        valid_file = examples_dir / test_case["valid_example"]
        invalid_file = examples_dir / test_case["invalid_example"]

        print(f"\n[*] Testing Schema: {schema_name} ({test_case['schema_file']})")

        # Step 1: Meta-Schema syntax check
        try:
            schema_data = validate_schema_structure(schema_file)
            print(f"  [+] Draft-07 Meta-Schema syntax: PASSED")
        except Exception as e:
            print(f"  [-] Draft-07 Meta-Schema syntax: FAILED -> {e}")
            all_passed = False
            continue

        validator = Draft7Validator(schema_data)

        # Step 2: Positive validation check
        try:
            valid_payload = load_json_file(valid_file)
            validator.validate(valid_payload)
            print(f"  [+] Positive Test ({test_case['valid_example']}): PASSED")
        except ValidationError as e:
            print(f"  [-] Positive Test ({test_case['valid_example']}): FAILED -> {e.message}")
            all_passed = False
            continue
        except Exception as e:
            print(f"  [-] Positive Test unexpected error: {e}")
            all_passed = False
            continue

        # Step 3: Negative validation check (must catch ValidationError)
        try:
            invalid_payload = load_json_file(invalid_file)
            validator.validate(invalid_payload)
            print(f"  [-] Negative Test ({test_case['invalid_example']}): FAILED (Did not reject invalid payload)")
            all_passed = False
            continue
        except ValidationError as e:
            print(f"  [+] Negative Test ({test_case['invalid_example']}): PASSED (Successfully caught expected violation: '{e.message}')")
        except Exception as e:
            print(f"  [-] Negative Test unexpected error: {e}")
            all_passed = False
            continue

        passed_schemas_count += 1

    print("\n------------------------------------------------------------------")
    print(f"Summary: {passed_schemas_count}/{len(schema_test_matrix)} Schemas fully validated.")
    if all_passed and passed_schemas_count == len(schema_test_matrix):
        print("STATUS: ALL AER PROTOCOL SCHEMAS VERIFIED SUCCESSFULLY (100%)")
        print("==================================================================")
        return True
    else:
        print("STATUS: VALIDATION FAILURES DETECTED")
        print("==================================================================")
        return False


def main() -> None:
    """Main CLI entrypoint."""
    success = run_schema_verification()
    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
