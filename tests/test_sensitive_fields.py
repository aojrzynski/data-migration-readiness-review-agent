from __future__ import annotations

import json
from pathlib import Path

from data_migration_readiness_review_agent.artifacts import SENSITIVE_FIELD_REVIEW_FILE_NAME
from helpers import FORBIDDEN_REVIEW_TERMS, make_pack, manifest_data, read_json, run_cli


def test_sensitive_field_review_is_written_and_flags_expected_columns(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = read_json(output_dir / SENSITIVE_FIELD_REVIEW_FILE_NAME)
    dataset = review["datasets"][0]
    source_flags = dataset["source"]["flagged_columns"]
    target_flags = dataset["target"]["flagged_columns"]
    assert review["status"] == "sensitive_field_review_created"
    assert {flag["column_name"] for flag in source_flags} >= {"email", "phone", "date_of_birth"}
    assert {flag["column_name"] for flag in target_flags} >= {"email", "phone", "date_of_birth"}
    assert any(flag["indicator_type"] == "manifest_hint" for flag in source_flags)
    assert review["summary"]["flagged_source_columns"] == 3


def test_builtin_patterns_and_normalized_case_insensitive_matching(tmp_path: Path) -> None:
    data = manifest_data()
    data["sensitive_field_hints"] = ["Tax ID"]
    pack_path = make_pack(tmp_path, data)
    for relative_path in ["data/source_customers.csv", "data/target_customers.csv"]:
        (pack_path / relative_path).write_text(
            "customer_id,Tax_ID,Postal-Code,Card Number\n1,abc,AB1 2CD,4111111111111111\n",
            encoding="utf-8",
        )
    (pack_path / "mappings/customer_mapping.csv").write_text(
        (
            "source_field,target_field\n"
            "customer_id,customer_id\n"
            "Tax_ID,Tax_ID\n"
            "Postal-Code,Postal-Code\n"
            "Card Number,Card Number\n"
        ),
        encoding="utf-8",
    )
    (pack_path / "contracts/customer_contract.yaml").write_text(
        "contract_id: customer_contract\ndataset_id: customers\nfields:\n"
        "  - name: Tax_ID\n    type: text\n    required: false\n"
        "  - name: Postal-Code\n    type: text\n    required: false\n"
        "  - name: Card Number\n    type: text\n    required: false\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = read_json(output_dir / SENSITIVE_FIELD_REVIEW_FILE_NAME)
    flags = review["datasets"][0]["source"]["flagged_columns"]
    by_name = {flag["column_name"]: flag for flag in flags}
    assert by_name["Tax_ID"]["indicator_type"] == "manifest_hint"
    assert by_name["Postal-Code"]["matched_indicator"] == "postal_code"
    assert by_name["Card Number"]["matched_indicator"] == "card_number"


def test_mapping_and_contract_mentions_include_flagged_fields(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    dataset = read_json(output_dir / SENSITIVE_FIELD_REVIEW_FILE_NAME)["datasets"][0]
    assert {mention["source_field"] for mention in dataset["mapping_mentions"]} >= {
        "email",
        "phone",
    }
    assert {mention["field_name"] for mention in dataset["contract_mentions"]} >= {"email", "phone"}


def test_sensitive_review_excludes_raw_values_and_forbidden_wording(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review_text = (output_dir / SENSITIVE_FIELD_REVIEW_FILE_NAME).read_text(encoding="utf-8")
    lowered = review_text.lower()
    assert "example@example.com" not in review_text
    assert "555-0100" not in review_text
    assert not any(term in lowered for term in FORBIDDEN_REVIEW_TERMS)
    assert "personal data confirmed" not in lowered
    assert "privacy approved" not in lowered


def test_missing_dataset_file_records_warning_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data/source_customers.csv").unlink()
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    source = read_json(output_dir / SENSITIVE_FIELD_REVIEW_FILE_NAME)["datasets"][0]["source"]
    assert source["status"] == "warning"
    assert source["warnings"]


def test_sensitive_review_artifact_contains_json_object(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    assert isinstance(json.loads((output_dir / SENSITIVE_FIELD_REVIEW_FILE_NAME).read_text()), dict)
