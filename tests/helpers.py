from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.artifacts import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    INVENTORY_FILE_NAME,
    LLM_REVIEWER_NOTES_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    TRACE_FILE_NAME,
)
from data_migration_readiness_review_agent.cli import main

EXPECTED_ARTIFACT_FILES = {
    INVENTORY_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    CONTRACT_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
    LLM_REVIEWER_NOTES_FILE_NAME,
    TRACE_FILE_NAME,
}

FORBIDDEN_REVIEW_TERMS = {
    "approved",
    "certified",
    "compliant",
    "go_live_approved",
    "go_live_ready",
    "go live ready",
    "ready for go-live",
    "safe to migrate",
    "migration is ready",
    "readiness score",
}


def manifest_data() -> dict[str, Any]:
    return {
        "migration": {
            "name": "customer_account_migration",
            "description": "Example migration pack.",
            "owner": "Example Data Migration Team",
            "source_system": "legacy_crm",
            "target_system": "new_customer_platform",
        },
        "datasets": [
            {
                "dataset_id": "customers",
                "source_path": "data/source_customers.csv",
                "target_path": "data/target_customers.csv",
                "key_columns": ["customer_id"],
                "row_count_tolerance": 0,
            }
        ],
        "mappings": [
            {
                "mapping_id": "customer_mapping",
                "dataset_id": "customers",
                "path": "mappings/customer_mapping.csv",
            }
        ],
        "contracts": [
            {
                "contract_id": "customer_contract",
                "dataset_id": "customers",
                "path": "contracts/customer_contract.yaml",
            }
        ],
        "test_results": [
            {"test_result_id": "migration_test_results", "path": "tests/test_results.csv"}
        ],
        "evidence": [
            {
                "evidence_id": "migration_notes",
                "evidence_type": "migration_notes",
                "path": "evidence/migration_notes.md",
            }
        ],
        "sensitive_field_hints": ["email", "phone"],
        "readiness_dimensions": ["scope_and_ownership"],
    }


def write_manifest(
    pack_path: Path, data: dict[str, Any] | None = None, name: str = "manifest.yaml"
) -> Path:
    manifest_path = pack_path / name
    manifest_path.write_text(json.dumps(data or manifest_data(), indent=2), encoding="utf-8")
    return manifest_path


def write_referenced_files(pack_path: Path) -> None:
    files = {
        "data/source_customers.csv": (
            "customer_id,email,phone,date_of_birth\n"
            "1,example@example.com,555-0100,1980-01-01\n"
            "2,second@example.com,555-0101,\n"
        ),
        "data/target_customers.csv": (
            "customer_id,email,phone,date_of_birth\n"
            "1,example@example.com,555-0100,1980-01-01\n"
            "2,second@example.com,555-0101,\n"
        ),
        "mappings/customer_mapping.csv": (
            "source_field,target_field\n"
            "customer_id,customer_id\n"
            "email,email\n"
            "phone,phone\n"
            "date_of_birth,date_of_birth\n"
        ),
        "contracts/customer_contract.yaml": (
            "contract_id: customer_contract\n"
            "dataset_id: customers\n"
            "fields:\n"
            "  - name: customer_id\n"
            "    type: integer\n"
            "    required: true\n"
            "  - name: email\n"
            "    type: text\n"
            "    required: true\n"
            "  - name: phone\n"
            "    type: text\n"
            "    required: false\n"
            "  - name: date_of_birth\n"
            "    type: date\n"
            "    required: false\n"
        ),
        "tests/test_results.csv": (
            "test_id,status,message\nexample_test,passed,Example migration test passed\n"
        ),
        "evidence/migration_notes.md": "# Notes\n",
    }
    for relative_path, content in files.items():
        path = pack_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def make_pack(tmp_path: Path, data: dict[str, Any] | None = None) -> Path:
    pack_path = tmp_path / "pack"
    pack_path.mkdir()
    write_manifest(pack_path, data)
    write_referenced_files(pack_path)
    return pack_path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cli(pack_path: Path, output_dir: Path, extra_args: list[str] | None = None) -> int:
    args = [
        "--pack",
        str(pack_path),
        "--output-dir",
        str(output_dir),
        "--no-llm",
        "--orchestrator",
        "standard",
    ]
    if extra_args:
        args.extend(extra_args)
    return main(args)
