from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INVENTORY_FILE_NAME = "migration_inventory.json"
DATASET_PROFILES_FILE_NAME = "dataset_profiles.json"
SCHEMA_INVENTORY_FILE_NAME = "schema_inventory.json"
MAPPING_REVIEW_FILE_NAME = "mapping_review.json"
CONTRACT_REVIEW_FILE_NAME = "contract_review.json"
RECONCILIATION_RESULTS_FILE_NAME = "reconciliation_results.json"
TRACE_FILE_NAME = "migration_readiness_trace.json"


def write_json_artifact(payload: dict[str, Any], output_dir: Path, file_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / file_name
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact_path
