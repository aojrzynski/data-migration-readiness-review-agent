from __future__ import annotations

import json
from pathlib import Path

from conftest import FORBIDDEN_REVIEW_TERMS, make_pack, read_json, run_cli
from data_migration_readiness_review_agent.artifacts import CONTRACT_REVIEW_FILE_NAME


def contract_review(output_dir: Path) -> dict:
    return read_json(output_dir / CONTRACT_REVIEW_FILE_NAME)["contract_reviews"][0]


def field_by_name(review: dict, name: str) -> dict:
    return next(field for field in review["contract_fields"] if field["name"] == name)


def test_valid_contract_review_is_written_and_checks_target_fields(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    artifact = read_json(output_dir / CONTRACT_REVIEW_FILE_NAME)
    review = artifact["contract_reviews"][0]
    assert artifact["status"] == "contract_review_created"
    assert review["status"] == "reviewed"
    assert review["field_count"] == 4
    assert review["required_field_count"] == 2
    assert review["missing_required_target_fields"] == []
    assert review["required_target_fields_with_nulls"] == []
    assert artifact["summary"]["contracts_reviewed"] == 1
    assert field_by_name(review, "customer_id")["status"] == "passed_check"


def test_contract_review_reports_required_nulls_type_warnings_and_extra_target_columns(
    tmp_path: Path,
) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "target_customers.csv").write_text(
        "customer_id,email,phone,date_of_birth,target_only\n"
        "1,,555-0100,1980-01-01,x\n"
        "2,second@example.com,555-0101,1981-01-01,y\n",
        encoding="utf-8",
    )
    (pack_path / "contracts" / "customer_contract.yaml").write_text(
        "contract_id: customer_contract\n"
        "dataset_id: customers\n"
        "fields:\n"
        "  - name: customer_id\n"
        "    type: text\n"
        "    required: true\n"
        "  - name: email\n"
        "    type: text\n"
        "    required: true\n"
        "  - name: phone\n"
        "    type: decimal\n"
        "    required: false\n"
        "  - name: missing_required\n"
        "    type: integer\n"
        "    required: true\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = contract_review(output_dir)
    assert review["status"] == "reviewed"
    assert review["missing_required_target_fields"] == ["missing_required"]
    assert review["required_target_fields_with_nulls"] == ["email"]
    assert review["target_columns_not_in_contract"] == ["date_of_birth", "target_only"]
    assert review["type_mismatch_warnings"]
    assert field_by_name(review, "customer_id")["checks"][-1]["status"] == "passed_check"
    assert field_by_name(review, "phone")["checks"][-1]["status"] == "warning"


def test_missing_contract_file_records_gap_found_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "contracts" / "customer_contract.yaml").unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    review = contract_review(output_dir)
    assert exit_code == 0
    assert review["status"] == "gap_found"
    assert "missing" in review["warnings"][0]


def test_malformed_contract_yaml_records_failed_check_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "contracts" / "customer_contract.yaml").write_text(
        "fields: [unterminated\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    review = contract_review(output_dir)
    assert exit_code == 0
    assert review["status"] == "failed_check"
    assert "could not be parsed" in review["warnings"][0]


def test_contract_with_missing_or_malformed_fields_records_failed_check(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "contracts" / "customer_contract.yaml").write_text(
        "contract_id: customer_contract\n"
        "fields:\n"
        "  - type: integer\n"
        "  - name: email\n"
        "    type: 123\n"
        "    required: not_bool\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    review = contract_review(output_dir)
    assert exit_code == 0
    assert review["status"] == "failed_check"
    assert any("missing a non-empty name" in warning for warning in review["warnings"])
    assert any("type must be a string" in warning for warning in review["warnings"])
    assert any("required flag must be a boolean" in warning for warning in review["warnings"])


def test_contract_fields_must_be_list(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "contracts" / "customer_contract.yaml").write_text(
        "contract_id: customer_contract\nfields: not-a-list\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = contract_review(output_dir)
    assert review["status"] == "failed_check"
    assert "fields' must be a list" in review["warnings"][0]


def test_contract_review_does_not_use_forbidden_approval_language(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    text = json.dumps(read_json(output_dir / CONTRACT_REVIEW_FILE_NAME)).lower()
    assert not any(term in text for term in FORBIDDEN_REVIEW_TERMS)
