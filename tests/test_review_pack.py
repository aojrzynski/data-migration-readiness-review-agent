from __future__ import annotations

import json
from pathlib import Path

from data_migration_readiness_review_agent.artifacts import REVIEW_PACK_FILE_NAME
from data_migration_readiness_review_agent.review_pack import SOURCE_ARTIFACTS
from data_migration_readiness_review_agent.safe_language import find_forbidden_terms
from helpers import (
    make_pack,
    manifest_data,
    read_json,
    run_cli,
    write_manifest,
    write_referenced_files,
)


def load_review_pack(tmp_path: Path, pack_path: Path) -> dict[str, object]:
    output_dir = tmp_path / "outputs"
    assert run_cli(pack_path, output_dir) == 0
    return read_json(output_dir / REVIEW_PACK_FILE_NAME)


def test_review_pack_is_written_with_metadata_source_artifacts_and_status(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    review_pack = load_review_pack(tmp_path, pack_path)

    assert review_pack["status"] == "review_pack_created"
    assert review_pack["migration"]["name"] == "customer_account_migration"
    assert review_pack["migration"]["owner"] == "Example Data Migration Team"
    assert review_pack["source_artifacts"] == SOURCE_ARTIFACTS


def test_review_pack_findings_have_required_fields_and_follow_up_status(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    review_pack = load_review_pack(tmp_path, pack_path)

    assert review_pack["findings"]
    for item in review_pack["findings"]:
        assert {"category", "status", "severity", "message", "source_artifact"} <= item.keys()
        assert item["evidence"]["artifact"] == item["source_artifact"]
    assert review_pack["follow_up_checklist"]
    assert {item["status"] for item in review_pack["follow_up_checklist"]} == {"follow_up_needed"}


def test_missing_referenced_files_produce_findings_and_follow_up_items(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "mappings" / "customer_mapping.csv").unlink()

    review_pack = load_review_pack(tmp_path, pack_path)

    assert any(item["category"] == "inventory" for item in review_pack["findings"])
    assert any(item["category"] == "mapping" for item in review_pack["findings"])
    assert any(item["category"] == "inventory" for item in review_pack["follow_up_checklist"])


def test_reconciliation_mismatches_produce_findings_and_follow_up_items(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    target = pack_path / "data" / "target_customers.csv"
    target.write_text(
        "customer_id,email,phone,date_of_birth\n"
        "1,changed@example.com,555-0100,1980-01-01\n"
        "2,second@example.com,555-0101,\n",
        encoding="utf-8",
    )

    review_pack = load_review_pack(tmp_path, pack_path)

    assert any(
        item["finding_id"] == "reconciliation:customers:mismatched_cells"
        for item in review_pack["findings"]
    )
    assert any(item["category"] == "reconciliation" for item in review_pack["follow_up_checklist"])


def test_sensitive_field_indicators_follow_up_without_confirmed_pii_language(
    tmp_path: Path,
) -> None:
    pack_path = make_pack(tmp_path)

    review_pack = load_review_pack(tmp_path, pack_path)
    text = json.dumps(review_pack).casefold()

    assert any(
        item["category"] == "sensitive_field_indicators"
        for item in review_pack["follow_up_checklist"]
    )
    assert "pii confirmed" not in text


def test_failed_warning_test_rows_and_missing_evidence_types_produce_findings(
    tmp_path: Path,
) -> None:
    data = manifest_data()
    data["evidence"] = []
    pack_path = tmp_path / "pack"
    pack_path.mkdir()
    write_manifest(pack_path, data)
    write_referenced_files(pack_path)
    (pack_path / "tests" / "test_results.csv").write_text(
        "test_id,status,message\ncheck_1,failed,Needs review\ncheck_2,warning,Warning row\n",
        encoding="utf-8",
    )

    review_pack = load_review_pack(tmp_path, pack_path)
    finding_ids = {item["finding_id"] for item in review_pack["findings"]}

    assert "test_evidence:migration_test_results:failed_like_rows" in finding_ids
    assert "test_evidence:migration_test_results:warning_like_rows" in finding_ids
    assert any(item["category"] == "evidence_coverage" for item in review_pack["findings"])


def test_review_pack_does_not_contain_forbidden_verdict_language(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    review_pack = load_review_pack(tmp_path, pack_path)

    assert find_forbidden_terms(json.dumps(review_pack)) == []
