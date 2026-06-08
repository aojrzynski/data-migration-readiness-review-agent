from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.artifacts import (
    RECONCILIATION_RESULTS_FILE_NAME,
    TRACE_FILE_NAME,
)
from helpers import FORBIDDEN_REVIEW_TERMS, make_pack, manifest_data, read_json, run_cli


def reconciliation(output_dir: Path) -> dict[str, Any]:
    return read_json(output_dir / RECONCILIATION_RESULTS_FILE_NAME)


def first_dataset(output_dir: Path) -> dict[str, Any]:
    return reconciliation(output_dir)["datasets"][0]


def write_customers(pack_path: Path, source_rows: list[str], target_rows: list[str]) -> None:
    header = "customer_id,email,phone,date_of_birth\n"
    (pack_path / "data" / "source_customers.csv").write_text(
        header + "\n".join(source_rows) + "\n", encoding="utf-8"
    )
    (pack_path / "data" / "target_customers.csv").write_text(
        header + "\n".join(target_rows) + "\n", encoding="utf-8"
    )


def run_reconciliation(tmp_path: Path, pack_path: Path) -> tuple[Path, dict[str, Any]]:
    output_dir = tmp_path / "outputs"
    run_cli(pack_path, output_dir)
    return output_dir, reconciliation(output_dir)


def test_reconciliation_results_json_is_written(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    assert (output_dir / RECONCILIATION_RESULTS_FILE_NAME).exists()


def test_clean_example_pack_reconciliation_passes_core_checks(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    output_dir, artifact = run_reconciliation(tmp_path, pack_path)

    dataset = first_dataset(output_dir)
    assert artifact["status"] == "reconciliation_created"
    assert dataset["row_count_check"]["status"] == "passed_check"
    assert dataset["key_overlap"]["missing_source_keys_in_target_count"] == 0
    assert dataset["key_overlap"]["unexpected_target_keys_count"] == 0
    assert dataset["field_comparison"]["mismatched_cell_count"] == 0
    assert artifact["summary"]["mismatched_cells"] == 0


def test_row_count_outside_tolerance_fails_check(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    write_customers(
        pack_path,
        ["1,example@example.com,555-0100,1980-01-01", "2,second@example.com,555-0101,"],
        ["1,example@example.com,555-0100,1980-01-01"],
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    row_count_check = first_dataset(output_dir)["row_count_check"]
    assert row_count_check["difference"] == 1
    assert row_count_check["tolerance"] == 0
    assert row_count_check["status"] == "failed_check"


def test_row_count_within_tolerance_passes_check(tmp_path: Path) -> None:
    data = manifest_data()
    data["datasets"][0]["row_count_tolerance"] = 1
    pack_path = make_pack(tmp_path, data)
    write_customers(
        pack_path,
        ["1,example@example.com,555-0100,1980-01-01", "2,second@example.com,555-0101,"],
        ["1,example@example.com,555-0100,1980-01-01"],
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    row_count_check = first_dataset(output_dir)["row_count_check"]
    assert row_count_check["difference"] == 1
    assert row_count_check["status"] == "passed_check"


def test_missing_source_keys_in_target_are_counted_and_sampled(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    write_customers(
        pack_path,
        ["1,example@example.com,555-0100,1980-01-01", "2,second@example.com,555-0101,"],
        ["1,example@example.com,555-0100,1980-01-01"],
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    key_overlap = first_dataset(output_dir)["key_overlap"]
    assert key_overlap["status"] == "failed_check"
    assert key_overlap["missing_source_keys_in_target_count"] == 1
    assert key_overlap["missing_source_key_samples"] == [{"customer_id": "2"}]


def test_unexpected_target_keys_are_counted_and_sampled(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    write_customers(
        pack_path,
        ["1,example@example.com,555-0100,1980-01-01"],
        ["1,example@example.com,555-0100,1980-01-01", "2,second@example.com,555-0101,"],
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    key_overlap = first_dataset(output_dir)["key_overlap"]
    assert key_overlap["status"] == "failed_check"
    assert key_overlap["unexpected_target_keys_count"] == 1
    assert key_overlap["unexpected_target_key_samples"] == [{"customer_id": "2"}]


def test_mapped_field_mismatches_are_counted_and_sampled(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    write_customers(
        pack_path,
        ["1,example@example.com,555-0100,1980-01-01"],
        ["1,changed@example.com,555-0100,1980-01-01"],
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    field_comparison = first_dataset(output_dir)["field_comparison"]
    assert field_comparison["status"] == "failed_check"
    assert field_comparison["mismatched_cell_count"] == 1
    assert field_comparison["mismatch_samples"] == [
        {
            "key": {"customer_id": "1"},
            "source_field": "email",
            "target_field": "email",
            "source_value": "example@example.com",
            "target_value": "changed@example.com",
        }
    ]


def test_mismatch_samples_are_bounded(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    source_rows = [f"{index},source{index}@example.com,555-0100," for index in range(1, 61)]
    target_rows = [f"{index},target{index}@example.com,555-0100," for index in range(1, 61)]
    write_customers(pack_path, source_rows, target_rows)

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    field_comparison = first_dataset(output_dir)["field_comparison"]
    assert field_comparison["mismatched_cell_count"] == 60
    assert len(field_comparison["mismatch_samples"]) == 50


def test_key_samples_are_bounded(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    source_rows = [f"{index},source{index}@example.com,555-0100," for index in range(1, 31)]
    target_rows = [f"{index},target{index}@example.com,555-0100," for index in range(31, 61)]
    write_customers(pack_path, source_rows, target_rows)

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    key_overlap = first_dataset(output_dir)["key_overlap"]
    assert key_overlap["missing_source_keys_in_target_count"] == 30
    assert key_overlap["unexpected_target_keys_count"] == 30
    assert len(key_overlap["missing_source_key_samples"]) == 20
    assert len(key_overlap["unexpected_target_key_samples"]) == 20


def test_missing_key_columns_skip_key_overlap_and_field_comparison(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "target_customers.csv").write_text(
        "email,phone,date_of_birth\nexample@example.com,555-0100,1980-01-01\n",
        encoding="utf-8",
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    dataset = first_dataset(output_dir)
    assert dataset["status"] == "gap_found"
    assert dataset["key_overlap"]["status"] == "skipped"
    assert dataset["key_overlap"]["missing_target_key_columns"] == ["customer_id"]
    assert dataset["field_comparison"]["status"] == "skipped"


def test_duplicate_keys_produce_warning_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    write_customers(
        pack_path,
        [
            "1,example@example.com,555-0100,1980-01-01",
            "1,duplicate@example.com,555-0102,1980-01-02",
        ],
        ["1,example@example.com,555-0100,1980-01-01"],
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    dataset = first_dataset(output_dir)
    assert dataset["status"] == "warning"
    assert dataset["duplicate_key_counts"]["source_duplicate_key_count"] == 1
    assert dataset["key_overlap"]["status"] == "passed_check"


def test_transformed_mapping_rows_are_skipped_for_field_comparison(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "mappings" / "customer_mapping.csv").write_text(
        "source_field,target_field,transformation\n"
        "customer_id,customer_id,\n"
        "email,email,lowercase\n"
        "phone,phone,\n",
        encoding="utf-8",
    )

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    field_comparison = first_dataset(output_dir)["field_comparison"]
    assert field_comparison["status"] == "warning"
    assert field_comparison["mapped_fields_compared"] == 2
    assert field_comparison["skipped_mapping_count"] == 1
    assert field_comparison["skipped_mappings"][0]["reason"] == "skipped_transformed_mapping"


def test_missing_dataset_file_records_gap_and_skipped_reconciliation(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "target_customers.csv").unlink()

    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    dataset = first_dataset(output_dir)
    assert dataset["status"] == "gap_found"
    assert dataset["row_count_check"]["status"] == "skipped"
    assert dataset["key_overlap"]["status"] == "skipped"
    assert dataset["field_comparison"]["status"] == "skipped"


def test_reconciliation_output_avoids_forbidden_verdict_language(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir, _ = run_reconciliation(tmp_path, pack_path)

    text = json.dumps(read_json(output_dir / RECONCILIATION_RESULTS_FILE_NAME)).lower()

    assert "go_live" not in text
    assert "go-live" not in text
    assert not any(term in text for term in FORBIDDEN_REVIEW_TERMS)


def test_trace_includes_reconciliation_artifact_and_summary(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir, artifact = run_reconciliation(tmp_path, pack_path)

    trace = read_json(output_dir / TRACE_FILE_NAME)
    assert RECONCILIATION_RESULTS_FILE_NAME in trace["artifacts_written"]
    assert trace["reconciliation_summary"] == artifact["summary"]
    assert trace["status"] == "review_summary_artifacts_created"


def test_no_blocked_runtime_dependencies_are_added() -> None:
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8").lower()

    dependencies_block = pyproject_text.split("[project.optional-dependencies]", 1)[0]
    assert "openai" not in dependencies_block
    assert "graph = [" in pyproject_text
    assert "langgraph" in pyproject_text
    for dependency_name in ("pandas", "openpyxl"):
        assert dependency_name not in pyproject_text
