from __future__ import annotations

import json
from pathlib import Path

from conftest import make_pack, read_json, run_cli
from data_migration_readiness_review_agent.artifacts import SCHEMA_INVENTORY_FILE_NAME


def test_schema_inventory_includes_columns_overlap_and_not_assessed_status(
    tmp_path: Path,
) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        "customer_id,email,source_only\n1,a@example.com,legacy\n", encoding="utf-8"
    )
    (pack_path / "data" / "target_customers.csv").write_text(
        "customer_id,email,target_only\n1,a@example.com,new\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    inventory = read_json(output_dir / SCHEMA_INVENTORY_FILE_NAME)
    dataset = inventory["datasets"][0]
    assert inventory["status"] == "schema_inventory_created"
    assert dataset["status"] == "not_assessed"
    assert dataset["source"]["columns"] == ["customer_id", "email", "source_only"]
    assert dataset["target"]["columns"] == ["customer_id", "email", "target_only"]
    assert dataset["schema_overlap"] == {
        "shared_columns": ["customer_id", "email"],
        "source_only_columns": ["source_only"],
        "target_only_columns": ["target_only"],
    }
    assert "ready" not in json.dumps(dataset).lower()


def test_no_llm_or_langgraph_dependencies_are_required() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8").lower()
    assert "langgraph" not in pyproject
    assert "openai" not in pyproject
    assert "pandas" not in pyproject
    assert "openpyxl" not in pyproject
