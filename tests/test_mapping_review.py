from __future__ import annotations

import json
from pathlib import Path

from conftest import FORBIDDEN_REVIEW_TERMS, make_pack, read_json, run_cli
from data_migration_readiness_review_agent.artifacts import MAPPING_REVIEW_FILE_NAME


def mapping_review(output_dir: Path) -> dict:
    return read_json(output_dir / MAPPING_REVIEW_FILE_NAME)["mapping_reviews"][0]


def test_valid_mapping_review_is_written_and_checks_columns(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    artifact = read_json(output_dir / MAPPING_REVIEW_FILE_NAME)
    review = artifact["mapping_reviews"][0]
    assert artifact["status"] == "mapping_review_created"
    assert review["status"] == "reviewed"
    assert review["mapping_row_count"] == 4
    assert review["mapped_source_fields"] == ["customer_id", "email", "phone", "date_of_birth"]
    assert review["mapped_target_fields"] == ["customer_id", "email", "phone", "date_of_birth"]
    assert review["missing_source_field_references"] == []
    assert review["missing_target_field_references"] == []
    assert artifact["summary"]["mappings_reviewed"] == 1


def test_mapping_review_reports_missing_blank_duplicate_and_unmapped_fields(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "target_customers.csv").write_text(
        "customer_id,email,phone,date_of_birth,target_only\n"
        "1,example@example.com,555-0100,1980-01-01,x\n",
        encoding="utf-8",
    )
    (pack_path / "mappings" / "customer_mapping.csv").write_text(
        "source_field,target_field\n"
        "customer_id,customer_id\n"
        "customer_id,email\n"
        "email,email\n"
        "missing_source,phone\n"
        "phone,missing_target\n"
        ",date_of_birth\n"
        "date_of_birth,\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = mapping_review(output_dir)
    assert review["status"] == "reviewed"
    assert review["missing_source_field_references"] == ["missing_source"]
    assert review["missing_target_field_references"] == ["missing_target"]
    assert review["duplicate_source_mappings"] == ["customer_id"]
    assert review["duplicate_target_mappings"] == ["email"]
    assert review["unmapped_target_columns"] == ["target_only"]
    issue_names = {issue for row in review["rows_with_issues"] for issue in row["issues"]}
    assert {"blank_source_field", "blank_target_field"} <= issue_names


def test_missing_mapping_file_records_gap_found_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "mappings" / "customer_mapping.csv").unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    review = mapping_review(output_dir)
    assert exit_code == 0
    assert review["status"] == "gap_found"
    assert "missing" in review["warnings"][0]


def test_malformed_mapping_csv_records_failed_check_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "mappings" / "customer_mapping.csv").write_text(
        'source_field,target_field\ncustomer_id,"unterminated\n', encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    review = mapping_review(output_dir)
    assert exit_code == 0
    assert review["status"] == "failed_check"
    assert "could not be parsed" in review["warnings"][0]


def test_mapping_csv_missing_required_columns_records_failed_check(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "mappings" / "customer_mapping.csv").write_text(
        "source,target\ncustomer_id,customer_id\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = mapping_review(output_dir)
    assert review["status"] == "failed_check"
    assert review["missing_required_columns"] == ["source_field", "target_field"]


def test_mapping_review_does_not_use_forbidden_approval_language(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    text = json.dumps(read_json(output_dir / MAPPING_REVIEW_FILE_NAME)).lower()
    assert not any(term in text for term in FORBIDDEN_REVIEW_TERMS)
