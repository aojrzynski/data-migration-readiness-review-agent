from __future__ import annotations

from pathlib import Path

from data_migration_readiness_review_agent.artifacts import INVENTORY_FILE_NAME
from helpers import make_pack, read_json, run_cli


def test_inventory_includes_metadata_datasets_referenced_files_and_counts(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    inventory = read_json(output_dir / INVENTORY_FILE_NAME)
    assert inventory["status"] == "inventory_created"
    assert inventory["migration"]["name"] == "customer_account_migration"
    assert inventory["datasets"][0]["dataset_id"] == "customers"
    assert inventory["datasets"][0]["status"] == "not_assessed"
    assert inventory["counts"] == {
        "datasets": 1,
        "referenced_files": 6,
        "referenced_files_present": 6,
        "referenced_files_missing": 0,
    }
    assert {item["status"] for item in inventory["referenced_files"]} == {"evidence_present"}
    assert inventory["gaps"] == []


def test_missing_referenced_files_get_gap_found_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "evidence" / "migration_notes.md").unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    inventory = read_json(output_dir / INVENTORY_FILE_NAME)
    assert exit_code == 0
    assert inventory["counts"]["referenced_files"] == 6
    assert inventory["counts"]["referenced_files_present"] == 5
    assert inventory["counts"]["referenced_files_missing"] == 1
    assert inventory["gaps"][0]["status"] == "gap_found"
    missing_file = next(
        item
        for item in inventory["referenced_files"]
        if item["path"] == "evidence/migration_notes.md"
    )
    assert missing_file["status"] == "referenced_file_missing"
